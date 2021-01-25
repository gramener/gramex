import os
import time
import tornado.gen
import gramex.data
import sqlalchemy as sa
from string import ascii_lowercase, digits
from random import choice
from mimetypes import guess_type
from tornado.web import HTTPError
from gramex.config import objectpath, slug
from gramex.http import NOT_FOUND, REQUEST_ENTITY_TOO_LARGE, UNSUPPORTED_MEDIA_TYPE
from .formhandler import FormHandler


class DriveHandler(FormHandler):
    '''
    Lets users manage files. Here's a typical configuration::

        path: $GRAMEXDATA/apps/appname/     # Save files here
        user_fields: [id, role, hd]         # user attributes to store
        tags: [tag]                         # <input name=""> to store
        allow: [.doc, .docx]                # Only allow these files
        ignore: [.pdf]                      # Don't allow these files
        max_file_size: 100000               # Files must be smaller than this
        redirect:                           # After uploading the file,
            query: next                     #   ... redirect to ?next=
            url: /$YAMLURL/                 #   ... else to this directory

    File metadata is stored in <path>/.meta.db as SQLite
    '''
    @classmethod
    def setup(cls, path, user_fields=None, tags=None, allow=None, ignore=None, max_file_size=None,
              **kwargs):
        cls.path = path
        cls.user_fields = cls._ensure_type('user_fields', user_fields)
        cls.tags = cls._ensure_type('tags', tags)
        cls.allow = allow or []
        cls.ignore = ignore or []
        cls.max_file_size = max_file_size or 0
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        # Set up the parent FormHandler with a single SQLite URL and table
        url, table = 'sqlite:///' + os.path.join(path, '.meta.db'), 'drive'
        kwargs.update(url=url, table=table, id='id')
        cls.special_keys += ['path', 'user_fields', 'tags', 'allow', 'ignore', 'max_file_size']
        super().setup(**kwargs)

        # Ensure all tags and user_fields are present in "drive" table
        engine = sa.create_engine(url)
        meta = sa.MetaData(bind=engine)
        meta.reflect()
        cls._db_cols = {
            'id': sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            'file': sa.Column('file', sa.Text),             # Original file name
            'ext': sa.Column('ext', sa.Text),               # Original file extension
            'path': sa.Column('path', sa.Text),             # Saved file relative path
            'size': sa.Column('size', sa.Integer),          # File size
            'mime': sa.Column('mime', sa.Text),             # MIME type
            'date': sa.Column('date', sa.Integer),          # Uploaded date
        }
        for s in cls.user_fields:
            cls._db_cols['user_%s' % s] = sa.Column('user_%s' % s, sa.String)
        for s in cls.tags:
            cls._db_cols.setdefault(s, sa.Column(s, sa.String))
        if table in meta.tables:
            with engine.connect() as conn:
                with conn.begin():
                    for col, coltype in cls._db_cols.items():
                        if col not in meta.tables[table].columns:
                            conn.execute('ALTER TABLE %s ADD COLUMN %s TEXT' % (table, col))
        else:
            sa.Table(table, meta, *cls._db_cols.values()).create(engine)

        # If ?_download=...&id=..., then download the file via modify:
        def download_plugin(data, key, handler):
            data = original_modify(data, key, handler)
            ids = handler.args.get('id', [])
            if len(ids) != 1 or '_download' not in handler.args:
                return data
            if len(data) == 0:
                raise HTTPError(NOT_FOUND, 'No file record with id=%s' % ids[0])
            path = os.path.join(handler.path, data['path'][0])
            if not os.path.exists(path):
                raise HTTPError(NOT_FOUND, 'Missing file for id=%s' % ids[0])
            handler.set_header('Content-Type', data['mime'][0])
            handler.set_header('Content-Length', os.stat(path).st_size)
            handler.set_header(
                'Content-Disposition', 'attachment; filename="%s"' % data['file'][0])
            with open(path, 'rb') as handle:
                return handle.read()

        original_modify = cls.datasets['data'].get('modify', lambda v, *args: v)
        cls.datasets['data']['modify'] = download_plugin

    def check_filelimits(self):
        allow = set(ext.lower() for ext in self.allow)
        ignore = set(ext.lower() for ext in self.ignore)
        for name, ext, size in zip(self.args['file'], self.args['ext'], self.args['size']):
            if self.max_file_size and size > self.max_file_size:
                raise HTTPError(REQUEST_ENTITY_TOO_LARGE, '%s: %d > %d' % (
                    name, size, self.max_file_size))
            if ext in ignore or (allow and ext not in allow):
                raise HTTPError(UNSUPPORTED_MEDIA_TYPE, name)

    @tornado.gen.coroutine
    def post(self, *path_args, **path_kwargs):
        '''Saves uploaded files, then updates metadata DB'''
        user = self.current_user or {}
        uploads = self.request.files.get('file', [])
        n = len(uploads)
        # Initialize all DB columns (except ID) to have the same number of rows as uploads
        for key, col in list(self._db_cols.items())[1:]:
            self.args[key] = self.args.get(key, []) + [col.type.python_type()] * n
        for key in self.args:
            self.args[key] = self.args[key][:n]
        for i, upload in enumerate(uploads):
            file = os.path.basename(upload.get('filename', ''))
            ext = os.path.splitext(file)[1]
            path = slug.filename(file)
            while os.path.exists(os.path.join(self.path, path)):
                path = os.path.splitext(path)[0] + choice(digits + ascii_lowercase) + ext
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
                self.args['user_%s' % s.replace('.', '_')][i] = objectpath(user, s)
        self.check_filelimits()
        yield super().post(*path_args, **path_kwargs)
        for upload, path in zip(uploads, self.args['path']):
            with open(os.path.join(self.path, path), 'wb') as handle:
                handle.write(upload['body'])

    @tornado.gen.coroutine
    def delete(self, *path_args, **path_kwargs):
        '''Deletes files from metadata DB and from file system'''
        conf = self.datasets.data
        files = gramex.data.filter(conf.url, table=conf.table, args=self.args)
        result = yield super().delete(*path_args, **path_kwargs)
        for index, row in files.iterrows():
            path = os.path.join(self.path, row['path'])
            if os.path.exists(path):
                os.remove(path)
        return result

    @tornado.gen.coroutine
    def put(self, *path_args, **path_kwargs):
        '''Update attributes and files'''
        # PUT can update only 1 ID at a time. Use only the first upload, if any
        uploads = self.request.files.get('file', [])[:1]
        id = self.args.get('id', [-1])
        # User cannot change the path, size, date or user attributes
        for s in ('path', 'size', 'date'):
            self.args.pop(s, None)
        for s in self.user_fields:
            self.args.pop('user_%s' % s, None)
        # These are updated only when a file is uploaded
        if len(uploads):
            user = self.current_user or {}
            self.args.setdefault('size', []).append(len(uploads[0]['body']))
            self.args.setdefault('date', []).append(int(time.time()))
            for s in self.user_fields:
                self.args.setdefault('user_%s' % s.replace('.', '_'), []).append(
                    objectpath(user, s))
        conf = self.datasets.data
        files = gramex.data.filter(conf.url, table=conf.table, args={'id': id})
        result = yield super().put(*path_args, **path_kwargs)
        if len(uploads) and len(files):
            path = os.path.join(self.path, files['path'].iloc[0])
            with open(path, 'wb') as handle:
                handle.write(uploads[0]['body'])
        return result

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
        raise TypeError('%s: %s should be a dict, not %s' % (cls.name, field, values))
