from gramex import conf
from tornado.web import RequestHandler
from tornado.escape import json_decode


class BaseHandler(RequestHandler):

    def initialize(self, cache=None, **kwargs):
        if cache is not None:
            self.cachefile = cache(self)
            self.original_get = self.get
            self.get = self.cached_get

    def cached_get(self, *args, **kwargs):
        cached = self.cachefile.get()
        if cached is not None:
            self.write(cached)
        else:
            self.cachefile.wrap(self)
            self.original_get(*args, **kwargs)

    def get_current_user(self):
        app_auth = conf.app.settings.get('auth', False)
        route_auth = self.params.get('auth', app_auth)
        if not route_auth:
            return 'static'
        user_json = self.get_secure_cookie('user')
        if not user_json:
            return None
        return json_decode(user_json)
