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
        'auth': 'Could not log in user',
        'conn': 'Connection error at {host}',
        'search': 'Cannot get attributes for user on {host}',
    }

    def get(self):
        self.render(self.conf.kwargs.template, error=None, user=None)

    def report_error(self, code, exc_info=False):
        error = self.errors[code].format(host=self.conf.kwargs.host, args=self.request.arguments)
        app_log.error('LDAP: ' + error, exc_info=exc_info)
        self.render(self.conf.kwargs.template, error={'code': code, 'error': error})
        raise tornado.gen.Return()

    @tornado.gen.coroutine
    def post(self):
        import ldap3
        kwargs = self.conf.kwargs

        # First, bind the server with the provided user ID and password.
        q = {key: self.get_argument(key) for key in self.request.arguments}
        server = ldap3.Server(kwargs.host, kwargs.get('port'), kwargs.get('use_ssl', False))
        conn = ldap3.Connection(server, kwargs.user.format(**q), kwargs.password.format(**q))
        try:
            result = yield info.threadpool.submit(conn.bind)
            if result is False:
                self.report_error('auth', exc_info=False)
        except ldap3.LDAPException:
            self.report_error('conn', exc_info=True)

        # We now have a valid user. Get additional attributes
        self.session['user'] = {'dn': conn.user}
        try:
            result = yield info.threadpool.submit(conn.search, conn.user, '(objectClass=*)',
                                                  attributes=ldap3.ALL_ATTRIBUTES)
        except ldap3.LDAPException:
            self.report_error('search', exc_info=True)
        if result and len(conn.entries) > 0:
            # Attributes may continue binary data. Get the result as JSON and then use the dict
            import json
            self.session['user'].update(json.loads(conn.entries[0].entry_to_json()))

        self.redirect(self.session.get('next', '/'))
