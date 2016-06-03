import time
import logging
import tornado.web
import tornado.gen
from tornado.escape import json_encode, json_decode
from tornado.auth import GoogleOAuth2Mixin, FacebookGraphMixin, TwitterMixin
from gramex.config import check_old_certs, app_log
from .basehandler import BaseHandler


def now():
    return '{:0.3f}'.format(time.time())


class AuthHandler(BaseHandler):
    '''
    The parent handler for all Auth handlers.
    '''
    @classmethod
    def setup(cls, **kwargs):
        super(AuthHandler, cls).setup(**kwargs)
        check_old_certs()


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


@tornado.gen.coroutine
def async(method, *args, **kwargs):
    '''
    Generic coroutine for LDAP functions. LDAP offers async functions that
    return a message ID. We poll the LDAP object via ``.result()`` for a
    response and return it when available.
    '''
    message_id = method(*args, **kwargs)
    ldap_object = method.im_self
    while True:
        typ, data = ldap_object.result(message_id)
        if typ is not None:
            raise tornado.gen.Return(data)
        yield tornado.gen.sleep(kwargs.get('delay', default=0.05))


class LDAPAuth(AuthHandler):
    errors = {
        'no-user': 'No user named %s',
        'no-pass': 'Invalid credentials for %s',
        'other': 'Could not log in %s',
    }

    @classmethod
    def setup(cls, **kwargs):
        super(LDAPAuth, cls).setup(**kwargs)

        import ldap
        for key, value in kwargs.get('options', {}).items():
            try:
                ldap.set_option(getattr(ldap, key, key), getattr(ldap, value, value))
            except Exception:
                app_log.exception('LDAP:%s: invalid option %s=%s', cls.name, key, value)
        cls.template = kwargs['template']
        cls.base = kwargs['base']
        cls.ldap = ldap.initialize(kwargs['url'])
        if kwargs.get('tls'):
            try:
                # setup() is not a coroutine, so stick to the synchronous method
                cls.ldap.start_tls_s()
            except ldap.CONNECT_ERROR:
                app_log.exception('LDAP:%s: cannot connect via TLS' % cls.name)
        cls.user_attr = kwargs.get('user', 'uid')

    def get(self):
        self.render(self.template, error=None)

    @tornado.gen.coroutine
    def post(self):
        user, password = self.get_argument('user'), self.get_argument('password')

        def report_error(level, error, exc_info=False):
            self.render(self.template, error=error, user=user)
            app_log.log(level, 'LDAP: ' + self.errors[error] % user, exc_info=exc_info)

        import ldap
        udn = yield async(self.ldap.search, self.base, ldap.SCOPE_SUBTREE,
                          '(%s=%s)' % (self.user_attr, user))
        if not udn:
            report_error(logging.INFO, error='no-user')
        else:
            try:
                yield async(self.ldap.simple_bind, udn[0][0], password)
            except ldap.INVALID_CREDENTIALS, ldap.UNWILLING_TO_PERFORM:
                app_log.info('LDAP: ' + self.errors['no-pass'])
                report_error(logging.DEBUG, error='no-pass', exc_info=True)
            except ldap.LDAPError:
                report_error(logging.INFO, error='other', exc_info=True)
            else:
                self.session['user'] = user
                self.redirect('.')
