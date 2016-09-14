import os
import time
import json
import gramex
import mimetypes
import tornado.gen
from orderedattrdict import AttrDict
from gramex.config import app_log
from gramex.transforms import build_transform
from .basehandler import BaseHandler, HDF5Store

MILLISECONDS = 1000


class FileUpload(object):
    stores = {}

    def __init__(self, path, keys=None, **kwargs):
        if keys is None:
            keys = {'file': ['file'], 'delete': ['delete']}
        self.path = os.path.abspath(path)
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        if self.path not in self.stores:
            self.stores[self.path] = HDF5Store(os.path.join(self.path, '.meta.h5'))
        self.store = self.stores[self.path]
        self.keys = keys
        if 'file' not in keys:
            keys['file'] = ['file']
        self.keys['file'] = keys['file'] if isinstance(keys['file'], list) else [keys['file']]

    def info(self):
        store = self.store
        return {k: store.load(k) for k in store.keys()}

    def addfiles(self, handler):
        filemetas = []
        for key in self.keys.get('file', []):
            for upload in handler.request.files.get(key, []):
                original_name = upload.get('filename', None)
                filepath = self.uniq_filename(original_name)
                with open(filepath, 'wb') as handle:
                    handle.write(upload['body'])
                filename = os.path.basename(filepath)
                stat = os.stat(filepath)
                mime = upload['content_type'] or mimetypes.guess_type(filepath, strict=False)[0]
                filemeta = AttrDict({
                    'key': key,
                    'filename': original_name,
                    'file': filename,
                    'created': time.time() * MILLISECONDS,  # JS parseable timestamp
                    'user': handler.get_current_user(),
                    'size': stat.st_size,
                    'mime': mime or 'application/octet-stream',
                    'data': handler.request.arguments
                })
                filemeta = handler.transforms(filemeta)
                self.store.dump(filename, filemeta)
                filemetas.append(filemeta)
        return filemetas

    def deletefiles(self, handler):
        status = []
        for delete_key in self.keys.get('delete', []):
            for key in handler.get_arguments(delete_key):
                stat = {'success': False, 'key': key}
                if key in self.store.store:
                    path = os.path.join(self.path, key)
                    if os.path.exists(path):
                        os.remove(path)
                        del self.store.store[key]
                        stat['success'] = True
                status.append(stat)
        return status

    def uniq_filename(self, filename):
        name, ext = os.path.splitext(filename or 'noname.bin')
        filepath = os.path.join(self.path, name + ext)
        if not os.path.exists(filepath):
            return filepath
        i = 1
        name_pattern = os.path.join(self.path, name + '.%s' + ext)
        while os.path.exists(name_pattern % i):
            i += 1
        return name_pattern % i


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
    def setup(cls, path, keys=None, transform={}, methods=[], **kwargs):
        super(UploadHandler, cls).setup(**kwargs)
        cls.uploader = FileUpload(path, keys=keys)

        # methods=['get'] will show all file into as JSON on GET
        if not isinstance(methods, list):
            methods = [methods]
        methods = {method.lower() for method in methods}
        if 'get' in methods:
            cls.get = cls.fileinfo

        cls.transform = []
        if 'function' in transform:
            cls.transform.append(build_transform(
                    transform, vars=AttrDict((('content', None), ('handler', None))),
                    filename='url:%s' % cls.name))

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
