import os
import time
import json
import gramex
import mimetypes
import tornado.gen
from orderedattrdict import AttrDict
from gramex.transforms import build_transform
from .basehandler import BaseHandler, HDF5Store, redirected

MILLISECONDS = 1000


class FileUpload(object):
    stores = {}

    def __init__(self, path, keys='file', **kwargs):
        self.path = os.path.abspath(path)
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        if self.path not in self.stores:
            self.stores[self.path] = HDF5Store(os.path.join(self.path, '.meta.h5'))
        self.store = self.stores[self.path]
        self.keys = keys if isinstance(keys, list) else [keys]

    def addfiles(self, handler, *args, **kwargs):
        filemetas = []
        for key in self.keys:
            for upload in handler.request.files.get(key, []):
                original_name = upload.get('filename', None)
                filepath = self.uniq_filename(original_name)
                with open(filepath, 'wb') as handle:
                    handle.write(upload['body'])
                filename = os.path.basename(filepath)
                stat = os.stat(filepath)
                # TODO: what if the guess_type fails as well? octet-stream or something
                mime = upload['content_type'] or mimetypes.guess_type(filepath)[0]
                filemeta = AttrDict({
                    'key': key,
                    'filename': original_name,
                    'file': filename,
                    'created': time.time() * MILLISECONDS,  # JS parseable timestamp
                    'user': handler.get_current_user(),
                    'size': stat.st_size,
                    'mime': mime,
                    'data': handler.request.arguments
                })
                filemeta = handler.transforms(filemeta)
                self.store.dump(filename, filemeta)
                filemetas.append(filemeta)
        return filemetas

    def uniq_filename(self, filename):
        # TODO: what if filename is nonexistent, i.e. None or ''
        name, ext = os.path.splitext(filename)
        filepath = os.path.join(self.path, name + ext)
        if not os.path.exists(filepath):
            return filepath
        i = 1
        name_pattern = os.path.join(self.path, name + '.%s' + ext)
        while os.path.exists(name_pattern % i):
            i += 1
        return name_pattern % i


class UploadHandler(BaseHandler):
    @classmethod
    def setup(cls, path, keys='file', transform={}, methods=[], **kwargs):
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
            cls.transform.append(build_transform(transform, vars=AttrDict(content=None),
                                                 filename='url>%s' % cls.name))

    @tornado.gen.coroutine
    def fileinfo(self, *args, **kwargs):
        store = self.uploader.store
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({k: store.load(k) for k in store.keys()}, indent=2))

    @tornado.gen.coroutine
    @redirected
    def post(self, *args, **kwargs):
        content = yield gramex.service.threadpool.submit(self.uploader.addfiles, self)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(content, ensure_ascii=True, separators=(',', ':')))

    def transforms(self, content):
        for transform in self.transform:
            for value in transform(content):
                content = value
        return content
