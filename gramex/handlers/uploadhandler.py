import os
import six
import time
import json
import gramex
import mimetypes
import tornado.gen
from orderedattrdict import AttrDict
from gramex.transforms import build_transform
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

    def addfiles(self, handler, *args, **kwargs):
        files = handler.request.files
        filemetas = []
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
            filemeta = handler.transforms(filemeta)
            self.files.append(filemeta)
            self.store.dump(filename_, filemeta)
            filemetas.append(filemeta)
        return filemetas

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
    def setup(cls, transform={}, **kwargs):
        super(UploadHandler, cls).setup(**kwargs)
        cls.params = AttrDict(kwargs)
        cls.uploader = FileUpload(cls.params.path)

        cls.transform = []
        if 'function' in transform:
            cls.transform.append(build_transform(transform, vars=AttrDict(content=None),
                                                 filename='url>%s' % cls.name))

    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        content = yield gramex.service.threadpool.submit(self.uploader.addfiles, self)
        if not isinstance(content, (six.binary_type, six.text_type)):
            content = json.dumps(content, ensure_ascii=True, separators=(',', ':'))
        self.write(content)

    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        self.write(json.dumps(self.uploader.files))

    def transforms(self, content):
        for transform in self.transform:
            for value in transform(content):
                content = value
        return content
