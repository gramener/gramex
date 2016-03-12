import time
import json
import tornado.web
from tornado.web import RequestHandler
from tornado.escape import json_encode
from tornado.auth import GoogleOAuth2Mixin, FacebookGraphMixin


class GoogleAuth(RequestHandler, GoogleOAuth2Mixin):
    @tornado.gen.coroutine
    def get(self):
        redirect_uri = (self.request.protocol + '://' +
                        self.request.host +
                        self.request.path)
        if self.get_argument('code', False):
            access = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'))

            http_client = self.get_auth_http_client()
            response = yield http_client.fetch(
                'https://www.googleapis.com/oauth2/v1/userinfo?access_token=' +
                access["access_token"])
            user = json.loads(response.body)["email"]

            self.set_secure_cookie(self.settings['cookie_secret'],
                                   str(time.time()))
            self.set_secure_cookie('user', json_encode(user))
            self.redirect('/')
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings['google_oauth'].key,
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'})


class FacebookAuth(RequestHandler, FacebookGraphMixin):
    @tornado.gen.coroutine
    def get(self):
        redirect_uri = (self.request.protocol + '://' + self.request.host +
                        self.request.path)
        if self.get_argument("code", False):
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.settings["facebook_api_key"],
                client_secret=self.settings["facebook_secret"],
                code=self.get_argument("code"))
            self.set_secure_cookie(self.settings['cookie_secret'],
                                   str(time.time()))
            self.set_secure_cookie('user', json_encode(user['name']))
            self.redirect('/')
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings["facebook_api_key"],
                extra_params={
                    'fields': 'name,email,first_name,last_name,'
                              'gender,link,username,locale,timezone'})
