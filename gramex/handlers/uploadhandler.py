import os
import time
import json
import mimetypes
import tornado.gen
from orderedattrdict import AttrDict
from .basehandler import BaseHandler, HDF5Store


def memoize(f):
    """memoizer"""
    _memoized = {}

    def memoized(*args, **kwargs):
        key = pathkey(*args)
        if key not in _memoized:
            _memoized[key] = f(*args, **kwargs)
        return _memoized[key]
    return memoized


def pathkey(*args):
    if len(args) > 1:
        args = (os.path.join(*args), )
    return os.path.abspath(*args)


@memoize
class FileUpload(object):
    def __init__(self, *args, **kwargs):
        self.path = pathkey(*args)
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        self.store = HDF5Store(os.path.join(self.path, 'meta'))
        self.files = [self.store.load(k) for k in self.store.keys()]

    def addfile(self, handler, *args, **kwargs):
        files = handler.request.files
        for upload in files.get('file', []):
            filename, ext = os.path.splitext(upload['filename'])
            filepath = self.uniq_filename(filename, ext)
            filename_ = os.path.basename(filepath)
            with open(filepath, 'wb') as handle:
                handle.write(upload['body'])
            mime = upload['content_type'] or mimetypes.guess_type(filepath)[0]
            filemeta = AttrDict({
                'name': upload['filename'],
                'file': filename_,
                'created': time.time(),
                'user': handler.get_current_user(),
                'size': os.stat(filepath).st_size,
                'mime': mime,
                'data': handler.request.arguments})
            self.files.append(filemeta)
            self.store.dump(filename_, filemeta)
        return

    def uniq_filename(self, name, ext):
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
    def setup(cls, **kwargs):
        super(UploadHandler, cls).setup(**kwargs)
        cls.params = AttrDict(kwargs)
        cls.uploader = FileUpload(cls.params.path)

    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        self.uploader.addfile(self)
        self.write('File uploaded!')

    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        self.write(json.dumps(self.uploader.files))
