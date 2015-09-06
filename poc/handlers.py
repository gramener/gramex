import tornado.web
from confutil import python_name


class Function(tornado.web.RequestHandler):
    def initialize(self, function, kwargs={}, redirect=None):
        self.function = python_name(function)
        self.kwargs = kwargs
        self.redirect_url = redirect

    def get(self):
        self.function(**self.kwargs)
        self.redirect(self.redirect_url or self.request.headers.get('Referer', '/'))
