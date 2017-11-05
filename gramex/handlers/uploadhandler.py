from __future__ import unicode_literals
import os
import six
import time
import json
import gramex
import shutil
import mimetypes
import tornado.gen
from datetime import datetime
from six.moves import zip_longest
from orderedattrdict import AttrDict
from tornado.web import HTTPError
from gramex.config import app_log
from gramex.transforms import build_transform
from gramex.http import FORBIDDEN, INTERNAL_SERVER_ERROR
from .basehandler import BaseHandler, HDF5Store

MILLISECONDS = 1000


class FileUpload(object):
    stores = {}

    def __init__(self, path, keys=None, **kwargs):
        if keys is None:
            keys = {}
        for cat in ('file', 'delete', 'save'):
            keys.setdefault(cat, [cat])
            if not isinstance(keys[cat], list):
                if isinstance(keys[cat], six.string_types):
                    keys[cat] = [keys[cat]]
                else:
                    app_log.error('FileUpload: cat: %r must be a list or str', keys[cat])
        self.keys = keys
        self.path = os.path.abspath(path)
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        if self.path not in self.stores:
            # TODO: allow other stores. #62
            self.stores[self.path] = HDF5Store(os.path.join(self.path, '.meta.h5'), flush=5)
        self.store = self.stores[self.path]
        if 'file' not in keys:
            keys['file'] = ['file']
        self.keys['file'] = keys['file'] if isinstance(keys['file'], list) else [keys['file']]

    def info(self):
        store = self.store
        info = [(k, store.load(k)) for k in store.keys()]
        return {k: v for k, v in info if v is not None}

    def addfiles(self, handler):
        filemetas = []
        uploads = [upload for key in self.keys.get('file', [])
                   for upload in handler.request.files.get(key, [])]
        filenames = [name for key in self.keys.get('save', [])
                     for name in handler.args.get(key, [])]
        if_exists = getattr(handler, 'if_exists', 'unique')
        for upload, filename in zip_longest(uploads, filenames, fillvalue=None):
            filemeta = self.save_file(upload, filename, if_exists)
            key = filemeta['file']
            filemeta.update(
                key=key,
                user=handler.get_current_user(),
                data=handler.args,
            )
            filemeta = handler.transforms(filemeta)
            self.store.dump(key, filemeta)
            filemetas.append(filemeta)
        return filemetas

    def save_file(self, upload, filename, if_exists):
        original_name = upload.get('filename', None)
        filemeta = AttrDict(filename=original_name)
        filename = filename or original_name or 'data.bin'
        filepath = os.path.join(self.path, filename)
        # Security check: don't allow files to be written outside path:
        if not os.path.realpath(filepath).startswith(os.path.realpath(self.path)):
            raise HTTPError(FORBIDDEN, reason='FileUpload: filename %s is outside path: %s' % (
                filename, self.path))
        if os.path.exists(filepath):
            if if_exists == 'error':
                raise HTTPError(FORBIDDEN, reason='FileUpload: file exists: %s' % filename)
            elif if_exists == 'unique':
                # Rename to file.1.ext or file.2.ext etc -- whatever's available
                name, ext = os.path.splitext(filepath)
                name_pattern = name + '.%s' + ext
                i = 1
                while os.path.exists(name_pattern % i):
                    i += 1
                filepath = name_pattern % i
            elif if_exists == 'backup':
                name, ext = os.path.splitext(filepath)
                backup = '{}.{:%Y%m%d-%H%M%S}{}'.format(name, datetime.now(), ext)
                shutil.copyfile(filepath, backup)
                filemeta['backup'] = os.path.relpath(backup, self.path).replace(os.path.sep, '/')
            elif if_exists != 'overwrite':
                raise HTTPError(INTERNAL_SERVER_ERROR,
                                reason='FileUpload: if_exists: %s invalid' % if_exists)
        # Create the directory to write in, if reuqired
        folder = os.path.dirname(filepath)
        if not os.path.exists(folder):
            os.makedirs(folder)
        # Save the file
        with open(filepath, 'wb') as handle:
            handle.write(upload['body'])
        mime = upload['content_type'] or mimetypes.guess_type(filepath, strict=False)[0]
        filemeta.update(
            file=os.path.relpath(filepath, self.path).replace(os.path.sep, '/'),
            size=os.stat(filepath).st_size,
            mime=mime or 'application/octet-stream',
            created=time.time() * MILLISECONDS,  # JS parseable timestamp
        )
        return filemeta

    def deletefiles(self, handler):
        status = []
        for delete_key in self.keys.get('delete', []):
            for key in handler.args.get(delete_key, []):
                stat = {'success': False, 'key': key}
                if key in self.store.keys():
                    path = os.path.join(self.path, key)
                    if os.path.exists(path):
                        os.remove(path)
                        self.store.dump(key, None)
                        stat['success'] = True
                status.append(stat)
        return status


class UploadHandler(BaseHandler):
    '''
    UploadHandler lets users upload files. Here's a typical configuration::

        path: /$GRAMEXDATA/apps/appname/    # Save files here
        keys: [upload, file]                # <input name=""> can be upload / file
        redirect:                           # After uploading the file,
            query: next                     #   ... redirect to ?next=
            url: /$YAMLURL/                 #   ... else to this directory
    '''
    @classmethod
    def setup(cls, path, keys=None, if_exists='unique', transform=None, methods=[], **kwargs):
        super(UploadHandler, cls).setup(**kwargs)
        cls.if_exists = if_exists
        cls.uploader = FileUpload(path, keys=keys)

        # methods=['get'] will show all file into as JSON on GET
        if not isinstance(methods, list):
            methods = [methods]
        methods = {method.lower() for method in methods}
        if 'get' in methods:
            cls.get = cls.fileinfo

        cls.transform = []
        if transform is not None:
            if isinstance(transform, dict) and 'function' in transform:
                cls.transform.append(build_transform(
                    transform, vars=AttrDict((('content', None), ('handler', None))),
                    filename='url:%s' % cls.name))
            else:
                app_log.error('UploadHandler %s: no function: in transform: %r',
                              cls.name, transform)

    @tornado.gen.coroutine
    def fileinfo(self, *args, **kwargs):
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(self.uploader.info(), indent=2))

    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        if self.redirects:
            self.save_redirect_page()
        upload = yield gramex.service.threadpool.submit(self.uploader.addfiles, self)
        delete = yield gramex.service.threadpool.submit(self.uploader.deletefiles, self)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({'upload': upload, 'delete': delete},
                              ensure_ascii=True, separators=(',', ':')))
        if self.redirects:
            self.redirect_next()

    def transforms(self, content):
        for transform in self.transform:
            for value in transform(content, self):
                if isinstance(value, dict):
                    content = value
                elif value is not None:
                    app_log.error('UploadHandler %s: transform returned %r, not dict',
                                  self.name, value)
        return content
