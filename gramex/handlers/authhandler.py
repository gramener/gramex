import ssl
import time
import tornado.web
from tornado.web import RequestHandler
from tornado.escape import json_encode, json_decode
from tornado.httpclient import HTTPClient, AsyncHTTPClient
from tornado.auth import GoogleOAuth2Mixin, FacebookGraphMixin, TwitterMixin
from gramex.config import app_log


def now():
    return '{:0.3f}'.format(time.time())


class AuthHandler(RequestHandler):
    '''
    The parent handler for all Auth handlers. Does not derive from BaseHandler.
    It does not support caching or get_current_user().
    '''
    ssl_checked = False

    @classmethod
    def check_old_certs(cls):
        '''
        The latest SSL certificates from certifi don't work for Google Auth. Do
        a one-time check to access accounts.google.com. If it throws an SSL
        error, switch to old SSL certificates. See
        https://github.com/tornadoweb/tornado/issues/1534
        '''
        if not cls.ssl_checked:
            # Use HTTPClient to check instead of AsyncHTTPClient because it's synchronous.
            _client = HTTPClient()
            try:
                # Use accounts.google.com because we know it fails with new certifi certificates
                # cdn.redhat.com is another site that fails.
                _client.fetch("https://accounts.google.com/")
            except ssl.SSLError:
                try:
                    import certifi      # noqa: late import to minimise dependencies
                    AsyncHTTPClient.configure(None, defaults=dict(ca_certs=certifi.old_where()))
                    app_log.warn('Using old SSL certificates for compatibility')
                except ImportError:
                    pass
            except Exception:
                # Ignore any other kind of exception
                app_log.warn('Gramex has no direct Internet connection.')
            _client.close()
            cls.ssl_checked = True

    def initialize(self, **kwargs):
        self.check_old_certs()


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
