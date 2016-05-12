import time
import tornado.web
from tornado.web import RequestHandler
from tornado.escape import json_encode, json_decode
from tornado.auth import GoogleOAuth2Mixin, FacebookGraphMixin, TwitterMixin


def now():
    return '{:0.3f}'.format(time.time())


class AuthHandler(RequestHandler):
    '''
    The parent handler for all Auth handlers. Does not derive from BaseHandler.
    It does not support caching or get_current_user().
    '''
    def initialize(self, **kwargs):
        pass


class GoogleAuth(AuthHandler, GoogleOAuth2Mixin):
    @tornado.gen.coroutine
    def get(self):
        redirect_uri = '{0.protocol:s}://{0.host:s}{0.path:s}'.format(self.request)
        if self.get_argument('code', False):
            access = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'))

            http_client = self.get_auth_http_client()
            response = yield http_client.fetch(
                'https://www.googleapis.com/oauth2/v1/userinfo?access_token=' +
                access["access_token"])
            user = json_decode(response.body)["email"]

            self.set_secure_cookie(self.settings['cookie_secret'], now())
            self.set_secure_cookie('user', json_encode(user))
            self.redirect('/')
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings['google_oauth'].key,
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'})


class FacebookAuth(AuthHandler, FacebookGraphMixin):
    @tornado.gen.coroutine
    def get(self):
        redirect_uri = '{0.protocol:s}://{0.host:s}{0.path:s}'.format(self.request)
        if self.get_argument("code", False):
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.settings["facebook_api_key"],
                client_secret=self.settings["facebook_secret"],
                code=self.get_argument("code"))
            self.set_secure_cookie(self.settings['cookie_secret'], now())
            self.set_secure_cookie('user', json_encode(user['name']))
            self.redirect('/')
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings["facebook_api_key"],
                extra_params={
                    'fields': 'name,email,first_name,last_name,'
                              'gender,link,username,locale,timezone'})


class TwitterAuth(AuthHandler, TwitterMixin):
    @tornado.gen.coroutine
    def get(self):
        # TODO: Test
        redirect_uri = '{0.protocol:s}://{0.host:s}{0.path:s}'.format(self.request)
        if self.get_argument("oauth_token", None):
            user = yield self.get_authenticated_user()
            self.set_secure_cookie(self.settings['cookie_secret'], now())
            self.set_secure_cookie('user', json_encode(user['username']))
            self.redirect('/')
        else:
            yield self.authenticate_redirect(callback_uri=redirect_uri)
