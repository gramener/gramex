from gramex import conf
from tornado.web import RequestHandler
from tornado.escape import json_decode


class BaseHandler(RequestHandler):
    def get_current_user(self):
        app_auth = conf.app.settings.get('auth', False)
        route_auth = self.params.get('auth', app_auth)
        if not route_auth:
            return {'user': 'static'}
        user_json = self.get_secure_cookie('user')
        if not user_json:
            return None
        return json_decode(user_json)
