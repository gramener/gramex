import os
import posixpath
import time
import tornado.gen
import gramex.data
from string import ascii_lowercase, digits
from random import choice
from mimetypes import guess_type
from tornado.web import HTTPError
from gramex.config import objectpath, slug, variables
from gramex.http import NOT_FOUND, REQUEST_ENTITY_TOO_LARGE, UNSUPPORTED_MEDIA_TYPE
from .formhandler import FormHandler


class DriveHandler(FormHandler):
    '''
    Lets users manage files. Here's a typical configuration

    ```yaml
    path: $GRAMEXDATA/apps/appname/     # Save files here
    user_fields: [id, role, hd]         # user attributes to store
    tags: [tag]                         # <input name=""> to store
    allow: [.doc, .docx]                # Only allow these files
    ignore: [.pdf]                      # Don't allow these files
    max_file_size: 100000               # Files must be smaller than this
    url: $GRAMEXDATA/apps/appname/.meta.db  # Optional metadata DB
    table: drive                            # Optional metadata table
    redirect:                           # After uploading the file,
        query: next                     #   ... redirect to ?next=
        url: /$YAMLURL/                 #   ... else to this directory
    ```
    '''

    @classmethod
    def setup(
        cls,
        path=None,
        user_fields=None,
        tags=None,
        allow=None,
        ignore=None,
        max_file_size=None,
        url=None,
        table=None,
        storage: dict = None,
        **kwargs,
    ):
        if not path:
            folder = slug['filename'](cls.name)
            path = os.path.join(variables['GRAMEXDATA'], 'drivehandler', folder)
        cls.user_fields = cls._ensure_type('user_fields', user_fields)
        cls.tags = cls._ensure_type('tags', tags)
        cls.allow = allow or []
        cls.ignore = ignore or []
        cls.max_file_size = max_file_size or 0
        storage = storage or {'type': 'os'}
        if storage.get('type') not in storages:
            raise ValueError(f'{cls.name}: storage.type should be one of {list(storages)}')
        if storage.get('type') == 'os':
            storage['path'] = path
        cls.fs = storages[storage['type']](**storage)
        # Set up the parent FormHandler with a single URL and table
        if not url:
            url = 'sqlite:///' + os.path.join(path, '.meta.db')
            os.makedirs(path, exist_ok=True)
        table = table or 'drive'
        kwargs.update(url=url, table=table, id='id')
        cls.special_keys += ['path', 'user_fields', 'tags', 'allow', 'ignore', 'max_file_size']
        super().setup(**kwargs)

        # Ensure all tags and user_fields are present in "drive" table
        cls._db_cols = {
            'id': {'type': 'int', 'primary_key': True, 'autoincrement': True},
            'file': {'type': 'text'},  # Original file name
            'ext': {'type': 'text'},  # Original file extension
            'path': {'type': 'text'},  # Saved file relative path
            'size': {'type': 'int'},  # File size
            'mime': {'type': 'text'},  # MIME type
            'date': {'type': 'int'},  # Uploaded date
        }
        for s in cls.user_fields:
            cls._db_cols[f'user_{s}'] = {'type': 'text'}
        for s in cls.tags:
            cls._db_cols.setdefault(s, {'type': 'text'})
        gramex.data.alter(url, table, cls._db_cols)

        # If ?_download=...&id=..., then download the file via modify:
        def download_plugin(data, key, handler):
            data = original_modify(data, key, handler)
            ids = handler.args.get('id', [])
            if len(ids) != 1 or '_download' not in handler.args:
                return data
            if len(data) == 0:
                raise HTTPError(NOT_FOUND, f'No file record with id={ids[0]}')
            path = data['path'][0]
            if not cls.fs.exists(path):
                raise HTTPError(NOT_FOUND, f'Missing file for id={ids[0]}')
            handler.set_header('Content-Type', data['mime'][0])
            handler.set_header('Content-Length', cls.fs.size(path))
            handler.set_header('Content-Disposition', f'attachment; filename="{data["file"][0]}"')
            with cls.fs.open(path, 'rb') as handle:
                return handle.read()

        original_modify = cls.datasets['data'].get('modify', lambda v, *args: v)
        cls.datasets['data']['modify'] = download_plugin

    def check_filelimits(self):
        allow = {ext.lower() for ext in self.allow}
        ignore = {ext.lower() for ext in self.ignore}
        for name, ext, size in zip(self.args['file'], self.args['ext'], self.args['size']):
            if self.max_file_size and size > self.max_file_size:
                raise HTTPError(REQUEST_ENTITY_TOO_LARGE, f'{name}: {size} > {self.max_file_size}')
            if ext in ignore or (allow and ext not in allow):
                raise HTTPError(UNSUPPORTED_MEDIA_TYPE, name)

    @tornado.gen.coroutine
    def post(self, *path_args, **path_kwargs):
        '''Saves uploaded files, then updates metadata DB'''
        user = self.current_user or {}
        uploads = self.request.files.get('file', [])
        n = len(uploads)
        # Initialize all DB columns (except ID) to have the same number of rows as uploads.
        # Add `n` rows, and then clip to `n` rows. Effective way to pad AND trim.
        for key in list(self._db_cols.keys())[1:]:
            self.args[key] = self.args.get(key, []) + [''] * n
        for key in self.args:
            self.args[key] = self.args[key][:n]
        for i, upload in enumerate(uploads):
            file = os.path.basename(upload.get('filename', ''))
            ext = os.path.splitext(file)[1]
            path = slug.filename(file)
            # B311:random random() is safe since it's for non-cryptographic use
            while self.fs.exists(path):
                randomletter = choice(digits + ascii_lowercase)  # noqa S311
                path = os.path.splitext(path)[0] + randomletter + ext
            self.args['file'][i] = file
            self.args['ext'][i] = ext.lower()
            self.args['path'][i] = path
            self.args['size'][i] = len(upload['body'])
            self.args['date'][i] = int(time.time())
            # Guess MIME type from filename if it's unknown
            self.args['mime'][i] = upload['content_type']
            if self.args['mime'][i] == 'application/unknown':
                self.args['mime'][i] = guess_type(file, strict=False)[0]
            # Append user attributes
            for s in self.user_fields:
                self.args[f'user_{s.replace(".", "_")}'][i] = objectpath(user, s)
        self.check_filelimits()
        self.files = self.args
        yield super().post(*path_args, **path_kwargs)

    def pre_modify(self, **kwargs):
        '''Called by FormHandler after updating the database, before modify. Save files here.

        This allows the DriveHandler modify: action to access the files.
        '''
        # If POST or PUT, save all files
        if self.request.method in {'POST', 'PUT'}:
            uploads = self.request.files.get('file', [])
            for upload, path in zip(uploads, self.files['path']):
                with self.fs.open(path, 'wb') as handle:
                    handle.write(upload['body'])
        elif self.request.method == 'DELETE':
            for path in self.files['path']:
                if self.fs.exists(path):
                    self.fs.remove(path)

    @tornado.gen.coroutine
    def delete(self, *path_args, **path_kwargs):
        '''Deletes files from metadata DB and from file system'''
        conf = self.datasets.data
        files = gramex.data.filter(conf.url, table=conf.table, args=self.args)
        self.files = files.to_dict(orient='list')
        yield super().delete(*path_args, **path_kwargs)

    @tornado.gen.coroutine
    def put(self, *path_args, **path_kwargs):
        '''Update attributes and files'''
        uploads = self.request.files.get('file', [])[:1]
        id = self.args.get('id', [-1])
        # User cannot change the path, size, date or user attributes
        for s in ('path', 'size', 'date'):
            self.args.pop(s, None)
        for s in self.user_fields:
            self.args.pop(f'user_{s}', None)
        # These are updated only when a file is uploaded
        if len(uploads):
            user = self.current_user or {}
            self.args.setdefault('size', []).append(len(uploads[0]['body']))
            self.args.setdefault('date', []).append(int(time.time()))
            for s in self.user_fields:
                self.args.setdefault(f'user_{s.replace(".", "_")}', []).append(objectpath(user, s))
        conf = self.datasets['data']
        files = gramex.data.filter(conf.url, table=conf.table, args={'id': id})
        self.files = files.to_dict(orient='list')
        self.files.update(self.args)
        yield super().put(*path_args, **path_kwargs)

    @classmethod
    def _ensure_type(cls, field, values):
        if isinstance(values, dict):
            return values
        if isinstance(values, (list, tuple)):
            return {v: 'str' for v in values if v}
        if isinstance(values, str) and values:
            return {values: 'str'}
        if not values:
            return {}
        raise TypeError(f'{cls.name}: {field} should be a dict, not {values}')


class OSFS(object):
    def __init__(self, path, type='os'):
        self.path = path
        os.makedirs(path, exist_ok=True)

    def exists(self, path):
        return os.path.exists(os.path.join(self.path, path))

    def open(self, path, mode):
        return open(os.path.join(self.path, path), mode)

    def remove(self, path):
        return os.remove(os.path.join(self.path, path))

    def size(self, path):
        return os.stat(os.path.join(self.path, path)).st_size


class S3FS(object):
    def __init__(self, type='s3', bucket='drivehandler') -> None:
        import s3fs

        self.fs = s3fs.S3FileSystem()
        self.bucket = bucket
        self.fs.makedirs(bucket, exist_ok=True)

    def exists(self, path):
        return self.fs.exists(posixpath.join(self.bucket, path))

    def open(self, path, mode):
        return self.fs.open(posixpath.join(self.bucket, path), mode)

    def remove(self, path):
        return self.fs.rm_file(posixpath.join(self.bucket, path))

    def size(self, path):
        return self.fs.size(posixpath.join(self.bucket, path))


storages = {
    'os': OSFS,
    's3': S3FS,
}
