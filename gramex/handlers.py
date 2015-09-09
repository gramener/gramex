import os
import tornado.web
from .confutil import python_name


class Function(tornado.web.RequestHandler):
    def initialize(self, function, kwargs={}, redirect=None):
        self.function = python_name(function)
        self.kwargs = kwargs
        self.redirect_url = redirect

    def get(self):
        self.function(**self.kwargs)
        self.redirect(self.redirect_url or self.request.headers.get('Referer', '/'))


class DirectoryHandler(tornado.web.RequestHandler):
    def initialize(self, path):
        self.root = path

    def get(self, path):
        paths = self.request.uri.split('/', 2)
        fullpath = os.path.join(self.root, paths[-1])

        if os.path.isfile(fullpath):
            self.render(fullpath)
        elif os.path.exists(fullpath):
            body = '<h1>Index of %s </h1>' % fullpath
            for name in os.listdir(fullpath):
                body += ('<p><a href="%s">%s</a></p>' %
                         (name, name))
            self.write(body)
        else:
            self.write('Random Request')
