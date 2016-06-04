import logging
import functools
import tornado.web
import tornado.gen
from tornado.auth import (GoogleOAuth2Mixin, FacebookGraphMixin, TwitterMixin,
                          urllib_parse, _auth_return_future)
from gramex.config import check_old_certs, app_log
from gramex.services import info
from .basehandler import BaseHandler


class AuthHandler(BaseHandler):
    '''The parent handler for all Auth handlers.'''
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
            self.session['user'] = yield self.oauth2_request(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                access_token=access["access_token"])
            self.redirect(self.session.get('next', '/'))
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.conf.kwargs['key'],
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'})

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, code, callback):
        '''Override this method to use self.conf.kwargs instead of self.settings'''
        http = self.get_auth_http_client()
        body = urllib_parse.urlencode({
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": self.conf.kwargs['key'],
            "client_secret": self.conf.kwargs['secret'],
            "grant_type": "authorization_code",
        })
        http.fetch(self._OAUTH_ACCESS_TOKEN_URL,
                   functools.partial(self._on_access_token, callback),
                   method="POST", body=body,
                   headers={'Content-Type': 'application/x-www-form-urlencoded'})


class FacebookAuth(AuthHandler, FacebookGraphMixin):
    @tornado.gen.coroutine
    def get(self):
        redirect_uri = '{0.protocol:s}://{0.host:s}{0.path:s}'.format(self.request)
        if self.get_argument("code", False):
            self.session['user'] = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.conf.kwargs['key'],
                client_secret=self.conf.kwargs['secret'],
                code=self.get_argument('code'))
            self.redirect(self.session.get('next', '/'))
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.conf.kwargs['key'],
                extra_params={
                    'fields': ','.join(self.conf.kwargs.get('fields', [
                        'name', 'email', 'first_name', 'last_name', 'gender',
                        'link', 'username', 'locale', 'timezone',
                    ])),
                })


class TwitterAuth(AuthHandler, TwitterMixin):
    @tornado.gen.coroutine
    def get(self):
        if self.get_argument("oauth_token", None):
            self.session['user'] = yield self.get_authenticated_user()
            self.redirect(self.session.get('next', '/'))
        else:
            yield self.authenticate_redirect()

    def _oauth_consumer_token(self):
        return dict(key=self.conf.kwargs['key'], secret=self.conf.kwargs['secret'])


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
        'search': 'Unable to search for {user} on {url}',
        'user': 'No user named {user}',
        'password': 'Invalid credentials for {user}',
        'other': 'Could not log in {user}',
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
        cls.url = kwargs['url']
        cls.ldap = ldap.initialize(cls.url)
        cls.user_attr = kwargs.get('user', 'uid')
        cls.tls_checked = set()
        cls.errors.update(kwargs.get('errors', {}))

    def get(self):
        self.render(self.template, error=None, user=None)

    @tornado.gen.coroutine
    def post(self):
        user, password = self.get_argument('user'), self.get_argument('password')

        def report_error(level, code, exc_info=False):
            error = self.errors[code].format(url=self.url, user=user)
            app_log.log(level, 'LDAP: ' + error, exc_info=exc_info)
            self.render(self.template, error=error, user=user)
            raise tornado.gen.Return()

        import ldap

        # As setup() is not a coroutine, do a one-time TLS setup
        if not self.tls_checked and self.conf.kwargs.get('tls'):
            # Do not repeat the TLS check again
            self.tls_checked.add(True)
            try:
                yield info.threadpool.submit(self.ldap.start_tls_s)
            except Exception:
                # If we can't connect via TLS, that's OK, just continue
                app_log.error('LDAP: Cannot connect securely to %s', self.url, exc_info=True)

        # Search for the given user
        try:
            user_dn = yield async(self.ldap.search, self.base, ldap.SCOPE_SUBTREE,
                                  '(%s=%s)' % (self.user_attr, user))
        except ldap.LDAPError:
            report_error(logging.ERROR, code='search', exc_info=True)
        if not user_dn:
            report_error(logging.INFO, code='user')

        # Check for the password
        try:
            yield async(self.ldap.simple_bind, user_dn[0][0], password)
        except (ldap.INVALID_CREDENTIALS, ldap.UNWILLING_TO_PERFORM):
            report_error(logging.INFO, code='password', exc_info=False)
        except ldap.LDAPError:
            report_error(logging.ERROR, code='other', exc_info=True)

        # The return value is a list of search results. Take the first element.
        # This is a tuple (dn, {user_info}). Just take the user_info dict, and
        # add the dn as an item.
        self.session['user'] = user_dn[0][1]
        self.session['user']['dn'] = user_dn[0][0]
        self.redirect(self.session.get('next', '/'))
