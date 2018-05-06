from __future__ import unicode_literals
import os
import csv
import six
import json
import time
import uuid
import base64
import string
import logging
import functools
import tornado.web
import tornado.gen
import tornado.escape
import tornado.httpclient
from random import choice
from socket import gethostname
from cachetools import TTLCache
from tornado.auth import (GoogleOAuth2Mixin, FacebookGraphMixin, TwitterMixin,
                          OAuth2Mixin, urllib_parse, _auth_return_future)
from collections import Counter
from orderedattrdict import AttrDict
import gramex
import gramex.cache
from gramex.http import UNAUTHORIZED, BAD_REQUEST, INTERNAL_SERVER_ERROR
from gramex.config import check_old_certs, app_log, objectpath, str_utf8, merge
from gramex.transforms import build_transform
from .basehandler import BaseHandler, build_log_info, SQLiteStore

_auth_template = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'auth.template.html')
_forgot_template = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'forgot.template.html')
_signup_template = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'signup.template.html')
_user_info_path = os.path.join(gramex.variables.GRAMEXDATA, 'auth.user.db')
_user_info = SQLiteStore(_user_info_path, table='user')

# Python 3 csv.writer.writerow writes as str(), which is unicode in Py3.
# Python 2 csv.writer.writerow writes as str(), which is bytes in Py2.
# So we use cStringIO.StringIO in Py2 (which handles bytes).
# Since Py3 doesn't have cStringIO, we use io.StringIO (which handles unicode)
try:
    import cStringIO
    StringIOClass = cStringIO.StringIO
except ImportError:
    import io
    StringIOClass = io.StringIO


def csv_encode(values, *args, **kwargs):
    '''
    Encode an array of unicode values into a comma-separated string. All
    csv.writer parameters are valid.
    '''
    buf = StringIOClass()
    writer = csv.writer(buf, *args, **kwargs)
    writer.writerow([
        v if isinstance(v, six.text_type) else
        v.decode('utf-8') if isinstance(v, six.binary_type) else repr(v)
        for v in values])
    return buf.getvalue().strip()


class AuthHandler(BaseHandler):
    '''The parent handler for all Auth handlers.'''
    @classmethod
    def setup(cls, prepare=None, action=None, delay=None, session_expiry=None,
              session_inactive=None, user_key='user', lookup=None, **kwargs):
        # Switch SSL certificates if required to access Google, etc
        gramex.service.threadpool.submit(check_old_certs)

        # Set up default redirection based on ?next=...
        if 'redirect' not in kwargs:
            kwargs['redirect'] = AttrDict([('query', 'next'), ('header', 'Referer')])
        super(AuthHandler, cls).setup(**kwargs)

        # Set up logging for login/logout events
        logger = logging.getLogger('gramex.user')
        keys = objectpath(gramex.conf, 'log.handlers.user.keys', [])
        log_info = build_log_info(keys, 'event')
        cls.log_user_event = lambda handler, event: logger.info(log_info(handler, event))

        # Count failed logins
        cls.failed_logins = Counter()
        # Set delay for failed logins from the delay: parameter which can be a number or list
        default_delay = [1, 1, 5]
        cls.delay = delay
        if isinstance(cls.delay, list) and not all(isinstance(n, (int, float)) for n in cls.delay):
            app_log.warning('%s: Ignoring invalid delay: %r', cls.name, cls.delay)
            cls.delay = default_delay
        elif isinstance(cls.delay, (int, float)) or cls.delay is None:
            cls.delay = default_delay

        # Set up session user key, session expiry and inactive expiry
        cls.session_user_key = user_key
        cls.session_expiry = session_expiry
        cls.session_inactive = session_inactive

        cls.lookup = lookup
        if cls.lookup is not None:
            if isinstance(lookup, dict):
                cls.lookup_id = cls.lookup.pop('id', 'user')
            else:
                app_log.error('%s: lookup must be a dict, not %s', cls.name, cls.lookup)
                cls.lookup = None

        # Set up prepare
        cls.auth_methods = {}
        if prepare is not None:
            cls.auth_methods['prepare'] = build_transform(
                conf={'function': prepare},
                vars={'args': None, 'handler': None},
                filename='url:%s:prepare' % cls.name,
                iter=False)

        # Set up post-login actions
        cls.actions = []
        if action is not None:
            if not isinstance(action, list):
                action = [action]
            for conf in action:
                cls.actions.append(build_transform(
                    conf, vars=AttrDict(handler=None),
                    filename='url:%s:%s' % (cls.name, conf.function)))

    def prepare(self):
        super(AuthHandler, self).prepare()
        if 'prepare' in self.auth_methods:
            result = self.auth_methods['prepare'](args=self.args, handler=self)
            if result is not None:
                self.args = result

    @staticmethod
    def update_user(user_id, **kwargs):
        '''Update user login/logout event.'''
        info = _user_info.load(user_id)
        info.update(kwargs)
        _user_info.dump(user_id, info)

    @tornado.gen.coroutine
    def set_user(self, user, id):
        # Find session expiry time
        expires_days = self.session_expiry
        if isinstance(self.session_expiry, dict):
            # If session_expiry (se) is a dict, use se.values[args[se.key]]
            # Or else, default to se.default - or None
            default = self.session_expiry.get('default', None)
            key = self.session_expiry.get('key', None)
            val = self.get_arg(key, None)
            lookup = self.session_expiry.get('values', {})
            expires_days = lookup.get(val, default)

        # When user logs in, change session ID and invalidate old session
        # https://www.owasp.org/index.php/Session_fixation
        self.get_session(expires_days=expires_days, new=True)

        # The unique ID for a user varies across logins. For example, Google and
        # Facebook provide an "id", but for Twitter, it's "username". For LDAP,
        # it's "dn". Allow auth handlers to decide their own ID attribute and
        # store it as "id" for consistency. Logging depends on this, for example.
        user['id'] = user[id]
        self.session[self.session_user_key] = user
        self.failed_logins[user[id]] = 0

        # Extend user attributes looking up the user ID in a lookup table
        if self.lookup is not None:
            # Look up the user ID in the lookup table and fetch all matching rows
            users = yield gramex.service.threadpool.submit(
                gramex.data.filter, args={self.lookup_id: [user['id']]}, **self.lookup)
            if len(users) > 0 and self.lookup_id in users.columns:
                # Update the user attributes with the non-null items in the looked up row
                user.update({
                    key: val for key, val in users.iloc[0].iteritems()
                    if not gramex.data.pd.isnull(val)
                })

        self.update_user(user[id], active='y', **user)

        # If session_inactive: is specified, set expiry date on the session
        if self.session_inactive is not None:
            self.session['_i'] = self.session_inactive * 24 * 60 * 60

        # Run post-login events (e.g. ensure_single_session) specified in config
        for callback in self.actions:
            callback(self)
        self.log_user_event(event='login')

    @tornado.gen.coroutine
    def fail_user(self, user, id):
        '''
        When user login fails, delay response. Delay = self.delay[# of failures].
        Or use the last value in the self.delay[] array.
        Return # failures
        '''
        failures = self.failed_logins[user[id]] = self.failed_logins[user[id]] + 1
        index = failures - 1
        delay = self.delay[index] if index < len(self.delay) else self.delay[-1]
        yield tornado.gen.sleep(delay)

    def render_template(self, path, **kwargs):
        '''
        Like self.render(), but reloads updated templates.
        '''
        template = gramex.cache.open(path, 'template')
        namespace = self.get_template_namespace()
        namespace.update(kwargs)
        self.finish(template.generate(**namespace))


class LogoutHandler(AuthHandler):
    def get(self):
        self.save_redirect_page()
        for callback in self.actions:
            callback(self)
        self.log_user_event(event='logout')
        user = self.session.get(self.session_user_key, {})
        if 'id' in user:
            self.update_user(user['id'], active='')
        self.session.pop(self.session_user_key, None)
        if self.redirects:
            self.redirect_next()


class OAuth2(AuthHandler, OAuth2Mixin):
    '''
    The OAuth2 handler lets users log into any OAuth2 service. It accepts this
    configuration:

    :arg str client_id: Create an app with the OAuth2 provider to get this ID
    :arg str client_secret: Create an app with the OAuth2 provider to get this ID
    :arg dict authorize: Authorization endpoint configuration:
        - url: Authorization endpoint URL
        - scope: an optional a list of string scopes
        - extra_params: an optional dict of URL query params passed
    :arg dict access_token: Access token endpoint configuration
        - url: Access token endpoint URL
        - session_key: optional key in session to store access token information. \
            default: `access_token`
        - headers: optional dict containing HTTP headers to pass to access token URL. \
            By default, sets `User-Agent` to `Gramex/<version>`.
        - body: optional dict containing arguments to pass to access token URL \
            (e.g. `{grant_type: authorization_code}`)
    :arg dict user_info: Optional user information API endpoint
        - url: API endpoint to fetch URL
        - headers: optional dict containing HTTP headers to pass to user info URL. \
            e.g. `Authorization: 'Bearer {access_token}'`. \
            Default: `{User-Agent: Gramex/<version>}`
        - method: HTTP method to use (default: `GET`)
        - body: optional dict containing POST arguments to pass to user info URL
        - user_id: Attribute in the returned user object that holds the user ID. \
          This is used to identify the user uniquely. default: `id`
    :arg str user_key: optional key in session to store user information.
        default: `user`
    '''
    AUTHORIZE_DEFAULTS = {
        'scope': [],
        'extra_params': {},
        'response_type': 'code',
    }
    ACCESS_TOKEN_DEFAULTS = {
        'headers': {
            'User-Agent': 'Gramex/' + gramex.__version__
        },
        'body': {
            'redirect_uri': '{redirect_uri}',
            'code': '{code}',
            'client_id': '{client_id}',
            'client_secret': '{client_secret}',
        },
        'session_key': 'access_token'
    }
    USER_INFO_DEFAULTS = {
        'headers': {
            'User-Agent': 'Gramex/' + gramex.__version__
        },
        'user_id': 'id'
    }

    @classmethod
    def setup(cls, client_id, client_secret, authorize, access_token,
              user_info=None, **kwargs):
        super(OAuth2, cls).setup(**kwargs)
        cls.client_id = client_id
        cls.client_secret = client_secret

        cls._OAUTH_AUTHORIZE_URL = authorize.url
        cls._OAUTH_ACCESS_TOKEN_URL = access_token.url
        cls.authorize = merge(authorize, cls.AUTHORIZE_DEFAULTS, mode='setdefault')
        cls.access_token = merge(access_token, cls.ACCESS_TOKEN_DEFAULTS, mode='setdefault')
        cls.user_info = merge({} if user_info is None else user_info,
                              cls.USER_INFO_DEFAULTS, mode='setdefault')

    @tornado.gen.coroutine
    def get(self):
        redirect_uri = '{0.protocol:s}://{0.host:s}{0.path:s}'.format(self.request)
        code = self.get_arg('code', '')
        # Step 1: user visits this page and is redirected to the OAuth provider
        if not code:
            self.save_redirect_page()
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.client_id,
                client_secret=self.client_secret,
                extra_params=self.authorize.extra_params,
                scope=self.authorize.scope,
                response_type=self.authorize.response_type,
            )
        # Step 2: after logging in, user is redirected back here to continue
        else:
            # Step 2a: Exchange code for access token
            http = self.get_auth_http_client()
            params = {
                'name': self.name,
                "redirect_uri": redirect_uri,
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            response = yield http.fetch(
                self._OAUTH_ACCESS_TOKEN_URL, method='POST', raise_error=False,
                **self._request_conf(self.access_token, params))
            self.validate(response)
            # Parse the response based on the HTTP Content Type
            body = tornado.escape.native_str(response.body)
            mime_type = response.headers['Content-Type']
            if mime_type.startswith('application/x-www-form-urlencoded'):
                args = six.moves.urllib_parse.parse_qs(body)
                args = {key: value[-1] for key, value in args.items()}
            elif mime_type.startswith('application/json'):
                args = json.loads(body)
            else:
                self.validate(AttrDict(
                    error=True, code=BAD_REQUEST, reason='Invalid access token',
                    body=('Access token response not form-encoded nor JSON:\n\n' +
                          'Content-Type: %s\n\n%s') % (mime_type, body),
                    headers={}))
                raise tornado.gen.Return()
            # Save the returned session info in a config-specified session key.
            # This defaults to 'access_token'
            params.update(args)
            session_key = self.access_token['session_key']
            self.session[session_key] = args

            # Step 2b: Use access token to fetch the user info
            if 'url' in self.user_info:
                response = yield http.fetch(
                    self.user_info['url'].format(**params),
                    raise_error=False,
                    **self._request_conf(self.user_info, params))
                self.validate(response)
                try:
                    user = json.loads(response.body)
                except Exception:
                    self.validate(AttrDict(
                        error=True, code=BAD_REQUEST, reason='Invalid user JSON',
                        body='User info not JSON:\n\n%s' % response.body,
                        headers={}))
                else:
                    user_id = self.user_info['user_id']
                    yield self.set_user(user, id=user_id)
            self.redirect_next()

    def _request_conf(self, conf, params):
        result = {}
        if 'method' in conf:
            result['method'] = conf['method']
        if 'headers' in conf:
            result['headers'] = {
                key: val.format(**params) for key, val in conf['headers'].items()
            }
        if 'body' in conf:
            result['body'] = six.moves.urllib_parse.urlencode({
                key: val.format(**params) for key, val in conf['body'].items()
            })
        return result

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return tornado.httpclient.AsyncHTTPClient()

    def validate(self, response):
        if response.error:
            app_log.error(response.body)
            self.set_status(response.code, reason=response.reason)
            mime_type = response.headers.get('Content-Type', 'text/plain')
            self.set_header('Content-Type', mime_type)
            self.write(response.body)
            raise tornado.gen.Return()


class GoogleAuth(AuthHandler, GoogleOAuth2Mixin):
    @tornado.gen.coroutine
    def get(self):
        redirect_uri = '{0.protocol:s}://{0.host:s}{0.path:s}'.format(self.request)
        code = self.get_arg('code', '')
        if code:
            access = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=code)
            user = yield self.oauth2_request(
                'https://www.googleapis.com/oauth2/v1/userinfo',
                access_token=access['access_token'])
            yield self.set_user(user, id='email')
            self.session['google_access_token'] = access['access_token']
            self.redirect_next()
        else:
            self.save_redirect_page()
            # Ensure user-specified scope has 'profile' and 'email'
            scope = self.kwargs.get('scope', [])
            scope = scope if isinstance(scope, list) else [scope]
            scope = list(set(scope) | {'profile', 'email'})
            # Ensure extra_params has auto approval prompt
            extra_params = self.kwargs.get('extra_params', {})
            if 'approval_prompt' not in extra_params:
                extra_params['approval_prompt'] = 'auto'
            # Return the list
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.kwargs['key'],
                scope=scope,
                response_type='code',
                extra_params=extra_params)

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, code, callback):
        '''This Tornado method is overridden to use self.kwargs, not self.settings'''
        http = self.get_auth_http_client()
        body = urllib_parse.urlencode({
            'redirect_uri': redirect_uri,
            'code': code,
            'client_id': self.kwargs['key'],
            'client_secret': self.kwargs['secret'],
            'grant_type': 'authorization_code',
        })
        http.fetch(self._OAUTH_ACCESS_TOKEN_URL,
                   functools.partial(self._on_access_token, callback),
                   method='POST', body=body,
                   headers={'Content-Type': 'application/x-www-form-urlencoded'})


class FacebookAuth(AuthHandler, FacebookGraphMixin):
    @tornado.gen.coroutine
    def get(self):
        redirect_uri = '{0.protocol:s}://{0.host:s}{0.path:s}'.format(self.request)
        code = self.get_arg('code', '')
        if code:
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.kwargs['key'],
                client_secret=self.kwargs['secret'],
                code=code)
            yield self.set_user(user, id='id')
            self.redirect_next()
        else:
            self.save_redirect_page()
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.kwargs['key'],
                extra_params={
                    'fields': ','.join(self.kwargs.get('fields', [
                        'name', 'email', 'first_name', 'last_name', 'gender',
                        'link', 'username', 'locale', 'timezone',
                    ])),
                })


class TwitterAuth(AuthHandler, TwitterMixin):
    @tornado.gen.coroutine
    def get(self):
        oauth_token = self.get_arg('oauth_token', '')
        if oauth_token:
            user = yield self.get_authenticated_user()
            yield self.set_user(user, id='username')
            self.redirect_next()
        else:
            self.save_redirect_page()
            yield self.authenticate_redirect(callback_uri=self.request.protocol + "://" +
                                             self.request.host + self.request.uri)

    def _oauth_consumer_token(self):
        return dict(key=self.kwargs['key'], secret=self.kwargs['secret'])


class SAMLAuth(AuthHandler):
    '''
    SAML Authentication.

    Reference: https://github.com/onelogin/python3-saml

    Sample configuration::

        kwargs:
          sp_domain: myapp.gramener.com         # Domain where your app is hosted
          request_uri: ...                      # Path to your app
          https: true                           # Use HTTPS scheme for your app
          custom_base_path: $YAMLPATH/.saml/    # Path to settings.json & certs/
          lowercase_encoding: True              # True for ADFS
    '''
    @classmethod
    def setup(cls, sp_domain, custom_base_path, https, lowercase_encoding=True,
              request_uri='', **kwargs):
        super(SAMLAuth, cls).setup(**kwargs)
        cls.sp_domain = sp_domain
        cls.custom_base_path = custom_base_path
        cls.https = 'on' if https is True else 'off'
        cls.default_params = {
            'lowercase_urlencoding': lowercase_encoding,
            'request_uri': request_uri,
        }

    @tornado.gen.coroutine
    def get(self):
        '''Process sso request and metadata request.'''
        auth = self.initiate_saml_login()
        # SAML server requests metadata at https://<sp_domain>/<request_uri>?metadata
        if 'metadata' in self.args:
            settings = auth.get_settings()
            metadata = settings.get_sp_metadata()
            errors = settings.validate_metadata(metadata)
            if errors:
                app_log.error('%s: SAML metadata errors: %s', self.name, errors)
                raise tornado.web.HTTPError(INTERNAL_SERVER_ERROR, reason='Errors in metadata')
            self.set_header('Content-Type', 'text/xml')
            self.write(metadata)
        # Logout
        elif 'sls' in self.args:
            raise NotImplementedError()
        # Login redirect
        else:
            self.save_redirect_page()
            self.redirect(auth.login())

    @tornado.gen.coroutine
    def post(self):
        '''Validate and authenticate user based upon SAML response.'''
        auth = self.initiate_saml_login()

        # Process IDP response, and create session.
        if 'acs' in self.args:
            auth.process_response()
            errors = auth.get_errors()
            if errors:
                app_log.error('%s: SAML ACS error: %s', self.name, errors)
                raise tornado.gen.Return()
            yield self.set_user({
                'samlUserdata': auth.get_attributes(),
                'samlNameId': auth.get_nameid(),
                'samlSessionIndex': auth.get_session_index(),
            }, id='samlNameId')
            self.redirect_next()

    def initiate_saml_login(self):
        # TODO: onelogin is not part of requirements.txt. Add it
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        req = merge({
            'http_host': self.sp_domain,
            'https': self.https,
            'script_name': self.request.path,
            'get_data': self.request.query_arguments,
            'post_data': {k: v[0] for k, v in self.args.items()}
        }, self.default_params, mode='setdefault')
        return OneLogin_Saml2_Auth(req, custom_base_path=self.custom_base_path)


class LDAPAuth(AuthHandler):
    @classmethod
    def setup(cls, **kwargs):
        super(LDAPAuth, cls).setup(**kwargs)
        cls.template = kwargs.get('template', _auth_template)

    def get(self):
        self.save_redirect_page()
        self.render_template(self.template, error=None)

    errors = {
        'bind': 'Unable to log in bind.user at {host}',
        'conn': 'Connection error at {host}',
        'auth': 'Could not log in user',
        'search': 'Cannot get attributes for user on {host}',
    }

    def report_error(self, code, exc_info=False):
        error = self.errors[code].format(host=self.kwargs.host, args=self.args)
        app_log.error('LDAP: ' + error, exc_info=exc_info)
        self.log_user_event(event='fail')
        self.set_status(UNAUTHORIZED)
        self.set_header('Auth-Error', code)
        self.render_template(self.template, error={'code': code, 'error': error})
        raise tornado.gen.Return()

    @tornado.gen.coroutine
    def bind(self, server, user, password, error):
        import ldap3
        conn = ldap3.Connection(server, user, password)
        try:
            result = yield gramex.service.threadpool.submit(conn.bind)
            if not result:
                self.report_error(error, exc_info=False)
                conn = None
            raise tornado.gen.Return(conn)
        except ldap3.core.exceptions.LDAPException:
            self.report_error('conn', exc_info=True)

    @tornado.gen.coroutine
    def post(self):
        import ldap3
        kwargs = self.kwargs
        # First, bind the server with the provided user ID and password.
        q = {key: vals[0] for key, vals in self.args.items()}
        server = ldap3.Server(kwargs.host, kwargs.get('port'), kwargs.get('use_ssl', True))
        cred = kwargs.bind if 'bind' in kwargs else kwargs
        user, password = cred.user.format(**q), cred.password.format(**q)

        error_code = 'bind' if 'bind' in kwargs else 'auth'
        conn = yield self.bind(server, user, password, error_code)
        if not conn:
            return

        # search: for user attributes if specified
        if 'search' in kwargs:
            search_base = kwargs.search.base.format(**q)
            search_filter = kwargs.search.filter.format(**q)
            search_user = kwargs.search.get('user', '{dn}')
            try:
                result = conn.search(search_base, search_filter, attributes=ldap3.ALL_ATTRIBUTES)
                if not result or not len(conn.entries):
                    self.report_error('search', exc_info=False)
                user = json.loads(conn.entries[0].entry_to_json())
                attrs = user.get('attributes', {})
                attrs['dn'] = user.get('dn', '')
                user['user'] = search_user.format(**attrs)
            except ldap3.core.exceptions.LDAPException:
                self.report_error('conn', exc_info=True)

            if 'bind' in kwargs:
                # REBIND: ensure that the password matches
                validate_user = yield self.bind(
                    server, user['dn'], kwargs.search.password.format(**q), 'auth')
                if not validate_user:
                    return
        else:
            user = {'user': user}

        yield self.set_user(user, id='user')
        self.redirect_next()


class SimpleAuth(AuthHandler):
    '''
    Eventually, change this to use an abstract base class for local
    authentication methods -- i.e. where **we** render the login screen, not a third party service.

    The login page is rendered in case of a login error as well. The page is a
    Tornado template that is passed an ``error`` variable. ``error`` is ``None``
    by default. If the login fails, it must be a ``dict`` with attributes
    specific to the handler.

    The simplest configuration (``kwargs``) for SimpleAuth is::

        credentials:                        # Mapping of user IDs and passwords
            user1: password1                # user1 maps to password1
            user2: password2

    An alternate configuration is::

        credentials:                        # Mapping of user IDs and user info
            user1:                          # Each user ID has a dictionary of keys
                password: password1         # One of them MUST be password
                email: user1@example.org    # Any other attributes can be added
                role: employee              # These are available from the session info
            user2:
                password: password2
                email: user2@example.org
                role: manager

    The full configuration (``kwargs``) for SimpleAuth looks like this::

        template: $YAMLPATH/auth.template.html  # Render the login form template
        user:
            arg: user                       # ... the ?user= argument from the form.
        password:
            arg: password                   # ... the ?password= argument from the form
        data:
            ...                             # Same as above

    The login flow is as follows:

    1. User visits the SimpleAuth page => shows template (with the user name and password inputs)
    2. User enters user name and password, and submits. Browser redirects with a POST request
    3. Application checks username and password. On match, redirects.
    4. On any error, shows template (with error)
    '''
    @classmethod
    def setup(cls, **kwargs):
        super(SimpleAuth, cls).setup(**kwargs)
        cls.template = kwargs.get('template', _auth_template)
        cls.user = kwargs.get('user', AttrDict())
        cls.password = kwargs.get('password', AttrDict())
        cls.credentials = kwargs.get('credentials', {})
        cls.user.setdefault('arg', 'user')
        cls.password.setdefault('arg', 'password')

    @tornado.gen.coroutine
    def get(self):
        self.save_redirect_page()
        self.render_template(self.template, error=None)

    @tornado.gen.coroutine
    def post(self):
        user = self.get_arg(self.user.arg, None)
        password = self.get_arg(self.password.arg, None)
        info = self.credentials.get(user)
        if info == password:
            yield self.set_user({'user': user}, id='user')
            self.redirect_next()
        elif hasattr(info, 'get') and info.get('password', None) == password:
            info.setdefault('user', user)
            yield self.set_user(dict(info), id='user')
            self.redirect_next()
        else:
            yield self.fail_user({'user': user}, id='user')
            self.log_user_event(event='fail')
            self.set_status(UNAUTHORIZED)
            self.render_template(self.template, error={'code': 'auth', 'error': 'Cannot log in'})


class DBAuth(SimpleAuth):
    '''
    The configuration (``kwargs``) for DBAuth looks like this::

        template: $YAMLPATH/auth.template.html  # Render the login form template
        url: sqlite:///$YAMLPATH/auth.db    # List of users is in this sqlalchemy URL or file
        table: users                        # ... and this table (if url is a database)
        prepare: some_function(args)
        user:
            column: user                    # The users.user column is matched with
            arg: user                       # ... the ?user= argument from the form
        password:
            column: password                # The users.password column is matched with
            arg: password                   # ... the ?password= argument from the form
                                            # Optional encryption for password
            function: passlib.hash.sha256_crypt.encrypt(content, salt='secret-key')
        forgot:
            key: forgot                     # ?forgot= is used as the forgot password parameter
            arg: email                      # ?email= is used as the email parameter
            template: $YAMLPATH/forgot.html # Forgot password template
            minutes_to_expiry: 15           # Minutes after which the link will expire
            email_column: user              # Database table column with email ID
            email_from: email-service       # Name of the email service to use for sending emails
            email_as: email-id              # Name of the person sending email (optional)
            email_text: 'This email is for {user}, {email}'
        # signup: true                      # Enables signup using ?signup
        signup:
            key: signup                     # ?signup= is used as the signup parameter
            template: $YAMLPATH/signup.html # Signup template
            columns:                        # Mapping of URL query parameters to database columns
                name: user_name             # ?name= is saved in the user_name column
                gender: user_gender         # ?gender= is saved in the user_gender column
                                            # Other than email, all other columns are ignored
            validate: app.validate(args)    # Optional validation method is passed handler.args
                                            # This may raise an Exception or return False to stop.

    The login flow is as follows:

    1. User visits the DBAuth page => shows template (with the user name and password inputs)
    2. User enters user name and password, and submits. Browser redirects with a POST request
    3. Application checks username and password. On match, redirects.
    4. On any error, shows template (with error)

    The forgot password flow is as follows:

    1. User visits ``GET ?forgot`` => shows forgot password template (with the user name)
    2. User submits user name. Browser redirects to ``POST ?forgot&user=...``
    3. Application generates a new password link (valid for ``minutes_to_expiry`` minutes).
    4. Application emails new password link to the email ID associated with user
    5. User is sent to ``?forgot=<token>`` => shows forgot password template (with password)
    6. User submits new password (entered twice) => ``POST ?forgot=<token>&password=...``
    7. Application checks if token is valid. If yes, sets associated user's password and redirects
    8. On any error, shows forgot password template (with error)

    The signup password flow is as follows:

    1. User visits ``GET ?signup`` => show signup template
    2. User submits email and other information. Browser redirects to ``POST ?signup&...``
    3. Application checks if email exists => suggest password recovery
    4. Application validates fields using validation function if it exists
    5. Else, Application adds the following fields to the database:
        - fields mentioned in ``signup.columns:``
        - email from ``forgot.arg:`` into ``forgot.email_column:``
        - random password using into ``password.column`` - no encryption
    6. Application says "I've sent an email to reset password" (and does so)
    '''
    # Number of characters in password
    PASSWORD_LENGTH = 20
    PASSWORD_CHARS = string.digits + string.ascii_letters

    @classmethod
    def setup(cls, url, user, password, table=None, forgot=None, signup=None, **kwargs):
        super(DBAuth, cls).setup(user=user, password=password, **kwargs)
        cls.clear_special_keys(kwargs, 'template', 'delay', 'prepare', 'action',
                               'session_expiry', 'session_inactive')
        cls.forgot, cls.signup = forgot, signup
        cls.query_kwargs = {'url': url, 'table': table}
        cls.query_kwargs.update(kwargs)
        if isinstance(cls.forgot, AttrDict):
            default_minutes_to_expiry = 15
            cls.forgot.setdefault('template', _forgot_template)
            cls.forgot.setdefault('key', 'forgot')
            cls.forgot.setdefault('arg', 'email')
            cls.forgot.setdefault('email_column', 'email')
            cls.forgot.setdefault('minutes_to_expiry', default_minutes_to_expiry)
            cls.forgot.setdefault('email_subject', 'Password reset')
            cls.forgot.setdefault('email_as', None)
            cls.forgot.setdefault(
                'email_text', 'Visit {reset_url} to reset password for user {user} ({email})')
            cls.recover = cls.setup_recover_db()
            # TODO: default email_from to the first available email service
        if cls.signup is True:
            cls.signup = AttrDict()
        if isinstance(cls.signup, AttrDict):
            if not cls.forgot:
                app_log.error('url:%s.signup requires .forgot.email_column', cls.name)
            cls.signup.setdefault('template', _signup_template)
            cls.signup.setdefault('key', 'signup')
            cls.signup.setdefault('columns', {})
            if 'validate' in cls.signup:
                validate = cls.signup.validate
                if isinstance(validate, six.string_types):
                    validate = {'function': validate}
                cls.signup.validate = build_transform(
                    validate, vars=AttrDict(handler=None, args=None),
                    filename='url:%s:signup.validate' % cls.name, iter=False)
        cls.encrypt = []
        if 'function' in password:
            cls.encrypt.append(build_transform(
                password, vars=AttrDict(handler=None, content=None),
                filename='url:%s:encrypt' % (cls.name)))

    def _exec_query(self, query, engine):
        result = engine.execute(query)
        if result.returns_rows:
            return result.fetchone()

    def _recovery(self, query):
        # Run a query on the recovery engine
        return gramex.service.threadpool.submit(self._exec_query, query, self.recover['engine'])

    def report_error(self, status, event, error, data=None):
        '''
        Set the HTTP status. Log user event. Return an error object.
        '''
        self.set_status(status, reason=error)
        self.log_user_event(event='fail')
        return {'code': 'auth', 'error': data or error}

    def get(self):
        self.save_redirect_page()
        template = self.template
        if self.forgot and self.forgot.key in self.args:
            template = self.forgot.template
        elif self.signup and self.signup.key in self.args:
            template = self.signup.template
        self.render_template(template, error=None)

    @tornado.gen.coroutine
    def post(self):
        if self.forgot and self.forgot.key in self.args:
            yield self.forgot_password()
        elif self.signup and self.signup.key in self.args:
            yield self.signup_user()
        else:
            yield self.login()

    @tornado.gen.coroutine
    def login(self):
        user = self.get_arg(self.user.arg, None)
        password = self.get_arg(self.password.arg, None)
        for encrypt in self.encrypt:
            for result in encrypt(handler=self, content=password):
                password = result

        users = yield gramex.service.threadpool.submit(gramex.data.filter, args={
            self.user.column: [user],
            self.password.column: [password],
        }, **self.query_kwargs)
        if len(users) > 0:
            # Delete password from user object before storing it in the session
            del users[self.password.column]
            yield self.set_user(users.iloc[0].to_dict(), id=self.user.column)
            self.redirect_next()
        else:
            yield self.fail_user({'user': user}, 'user')
            self.render_template(self.template, error=self.report_error(
                UNAUTHORIZED, 'fail', 'Cannot log in'))

    @tornado.gen.coroutine
    def forgot_password(self):
        template = self.forgot.template
        error = {}
        forgot_key = self.get_arg(self.forgot.key, None)

        # Step 1: user submits their user ID / email via POST ?forgot&user=...
        if not forgot_key:
            # Get the user based on the user ID or email ID (in that priority)
            forgot_user = self.get_arg(self.user.arg, None)
            forgot_email = self.get_arg(self.forgot.arg, None)
            if forgot_user:
                query = {self.user.column: [forgot_user]}
            else:
                query = {self.forgot.email_column: [forgot_email]}
            users = yield gramex.service.threadpool.submit(
                gramex.data.filter, args=query, **self.query_kwargs)
            user = None if len(users) == 0 else users.iloc[0].to_dict()
            email_column = self.forgot.get('email_column', 'email')

            # If a matching user exists in the database
            if user is not None and user[email_column]:
                # generate token and set expiry
                token = uuid.uuid4().hex
                expire = time.time() + (self.forgot.minutes_to_expiry * 60)
                # store values into database
                values = {
                    'user': user[self.user.column],
                    'email': user[email_column],
                    'token': token,
                    'expire': expire}
                yield self._recovery(self.recover['table'].insert().values(values))
                # send password reset mail to user
                mailer = gramex.service.email[self.forgot.email_from]
                reset_url = self.request.protocol + '://' + self.request.host + self.request.path
                reset_url += '?' + urllib_parse.urlencode({self.forgot.key: token})
                kwargs = {
                    'to': user[email_column],
                    'subject': self.forgot.email_subject.format(reset_url=reset_url, **user),
                    'body': self.forgot.email_text.format(reset_url=reset_url, **user),
                }
                if self.forgot.email_as:
                    kwargs['from'] = self.forgot.email_as
                yield gramex.service.threadpool.submit(mailer.mail, **kwargs)
            # If no user matches the user ID or email ID
            else:
                if user is None:
                    msg = 'No user matching %s found' % (forgot_user or forgot_email)
                elif not user[email_column]:
                    msg = 'No email matching %s found' % (forgot_user or forgot_email)
                error = self.report_error(UNAUTHORIZED, 'forgot-nouser', msg)

        # Step 2: User clicks on email, submits new password via POST ?forgot=<token>&password=...
        else:
            where = self.recover['table'].c['token'] == forgot_key
            row = yield self._recovery(self.recover['table'].select().where(where))
            # if system generated token in database
            if row is not None:
                # if token is not expired
                if row['expire'] > time.time():
                    password = self.get_arg(self.password.arg, None)
                    for encrypt in self.encrypt:
                        for result in encrypt(handler=self, content=password):
                            password = result
                    # Update password in database
                    yield gramex.service.threadpool.submit(
                        gramex.data.update, id=[self.user.column], args={
                            self.user.column: [row['user']],
                            self.password.column: [password]
                        }, **self.query_kwargs)
                    # Remove recovery token
                    yield self._recovery(self.recover['table'].delete(where))
                else:
                    error = self.report_error(
                        UNAUTHORIZED, 'forgot-token-expired', 'Token expired')
            else:
                error = self.report_error(UNAUTHORIZED, 'forgot-token-invalid', 'Invalid Token')
        self.render_template(template, error=error)

    @tornado.gen.coroutine
    def signup_user(self):
        # Checks if email exists => suggest password recovery
        signup_user = self.get_arg(self.user.arg, None)
        users = yield gramex.service.threadpool.submit(
            gramex.data.filter, args={self.user.column: [signup_user]}, **self.query_kwargs)
        if len(users) > 0:
            self.render_template(self.signup.template, error=self.report_error(
                BAD_REQUEST, 'signup-exists', 'User exists'))
            raise tornado.gen.Return()

        # Validates fields using validation function if they exists
        if 'validate' in self.signup:
            validate_error = self.signup.validate(handler=self, args=self.args)
            if validate_error:
                self.render_template(self.signup.template, error=self.report_error(
                    BAD_REQUEST, 'signup-invalid', 'Validation failed', validate_error))
                raise tornado.gen.Return()

        # Else, add the following fields to the database:
        #  - fields mentioned in ``signup.columns:``
        #  - email from ``forgot.arg:`` into ``forgot.email_column:``
        #  - password using random 20 char password into ``password.column`` - no encryption
        pwd = ''.join(choice(self.PASSWORD_CHARS) for c in range(self.PASSWORD_LENGTH))   # nosec
        values = {
            self.user.column: [signup_user],
            # TODO: allow admins (maybe users) to enter their own passwords in case of no email
            self.password.column: [pwd],
        }
        for field, column in self.signup.columns.items():
            values[field] = self.args.get(column, [])
        if self.forgot and self.forgot.arg in self.args:
            values[self.forgot.email_column] = self.args.get(self.forgot.arg, [])
        yield gramex.service.threadpool.submit(
            gramex.data.insert, id=[self.user.column], args=values, **self.query_kwargs)

        # Send a password reset link
        yield self.forgot_password()

    @classmethod
    def setup_recover_db(cls):
        '''Set up the database that stores password recovery tokens'''
        from sqlalchemy import create_engine, MetaData, Table
        # create database at GRAMEXDATA locastion
        path = os.path.join(gramex.variables.GRAMEXDATA, 'auth.recover.db')
        url = 'sqlite:///{}'.format(path)
        engine = create_engine(url, encoding=str_utf8)
        conn = engine.connect()
        conn.execute('CREATE TABLE IF NOT EXISTS users '
                     '(user TEXT, email TEXT, token TEXT, expire REAL)')
        meta = MetaData(bind=engine)
        user_table = Table('users', meta, autoload=True, autoload_with=engine)
        return {'engine': engine, 'table': user_table}


class IntegratedAuth(AuthHandler):
    @classmethod
    def setup(cls, realm=None, maxsize=1000, ttl=300, **kwargs):
        super(IntegratedAuth, cls).setup(**kwargs)
        cls.realm = realm if realm is not None else gethostname()
        # Security contexts are stored in a dict with the session ID as keys.
        # Only retain the latest contexts, and limit the duration
        cls.csas = TTLCache(maxsize, ttl)

    def negotiate(self, msg=None):
        self.set_status(UNAUTHORIZED)
        self.add_header('WWW-Authenticate',
                        'Negotiate' if msg is None else 'Negotiate ' + msg)

    def unauthorized(self):
        self.log_user_event(event='fail')
        self.set_status(UNAUTHORIZED)
        self.csas.pop(self.session['id'], None)
        self.write('Unauthorized')

    @tornado.gen.coroutine
    def get(self):
        try:
            import sspi
            import sspicon
        except ImportError:
            app_log.exception('%s: requires Windows, sspi package', self.name)
            raise
        self.save_redirect_page()

        # Spec: https://tools.ietf.org/html/rfc4559
        challenge = self.request.headers.get('Authorization')
        if not challenge:
            self.negotiate()
            raise tornado.gen.Return()

        scheme, auth_data = challenge.split(None, 2)
        if scheme != 'Negotiate':
            app_log.error('%s: unsupported Authorization: %s', self.name, challenge)
            self.unauthorized()
            raise tornado.gen.Return()

        # Get the security context
        session_id = self.session['id']
        if session_id not in self.csas:
            realm = self.realm
            spn = 'http/%s' % realm
            self.csas[session_id] = yield gramex.service.threadpool.submit(
                sspi.ServerAuth, "Negotiate", spn=spn)
        csa = self.csas[session_id]

        try:
            err, sec_buffer = yield gramex.service.threadpool.submit(
                csa.authorize, base64.b64decode(auth_data))
        except Exception:
            # The token may be invalid, password may be wrong, or server unavailable
            app_log.exception('%s: authorize() failed on: %s', self.name, auth_data)
            self.unauthorized()
            raise tornado.gen.Return()

        # If SEC_I_CONTINUE_NEEDED, send challenge again
        # If err is anything other than zero, we don't know what it is
        if err == sspicon.SEC_I_CONTINUE_NEEDED:
            self.negotiate(base64.b64encode(sec_buffer[0].Buffer))
            raise tornado.gen.Return()
        elif err != 0:
            app_log.error('%s: authorize() unknown response: %s', self.name, err)
            self.unauthorized()
            raise tornado.gen.Return()

        # The security context contains the user ID. Retrieve it.
        # Split the DOMAIN\username into its parts. Add to the user object
        user_id = yield gramex.service.threadpool.submit(
            csa.ctxt.QueryContextAttributes, sspicon.SECPKG_ATTR_NAMES)
        parts = user_id.split('\\', 2)
        user = {
            'id': user_id,
            'domain': parts[0] if len(parts) > 1 else '',
            'username': parts[-1],
            'realm': self.realm,
        }
        self.csas.pop(session_id, None)

        yield self.set_user(user, 'id')
        self.redirect_next()
