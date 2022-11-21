from fnmatch import fnmatch
import os
import json
import logging
import tornado.escape
import tornado.httpclient
from tornado.auth import GoogleOAuth2Mixin
from tornado.gen import coroutine, sleep
from tornado.web import HTTPError
from urllib.parse import urlencode
from collections import Counter
from orderedattrdict import AttrDict
import gramex
import gramex.cache
from gramex.http import UNAUTHORIZED, FORBIDDEN
from gramex.config import app_log, objectpath, merge
from gramex.transforms import build_transform
from .basehandler import BaseHandler, build_log_info

_folder = os.path.dirname(os.path.abspath(__file__))
_auth_template = os.path.join(_folder, 'auth.template.html')
_user_info_path = os.path.join(gramex.variables.GRAMEXDATA, 'auth.user.db')
_user_info = gramex.cache.SQLiteStore(_user_info_path, table='user')


class AuthHandler(BaseHandler):
    '''The parent handler for all Auth handlers.'''

    _RECAPTCHA_VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'

    @classmethod
    def setup(
        cls,
        prepare=None,
        action=None,
        delay=None,
        session_expiry=None,
        session_inactive=None,
        user_key='user',
        lookup=None,
        recaptcha=None,
        rules=None,
        **kwargs,
    ):
        # Set up default redirection based on ?next=...
        if 'redirect' not in kwargs:
            kwargs['redirect'] = AttrDict([('query', 'next'), ('header', 'Referer')])
        cls.special_keys += ['rules']
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
        cls.delay = default_delay if delay is None else delay
        if not isinstance(cls.delay, list):
            cls.delay = [cls.delay]
        if not all(isinstance(n, (int, float)) for n in cls.delay):
            app_log.warning(f'{cls.name}: Ignoring invalid delay: {cls.delay!r}')
            cls.delay = default_delay

        # Set up session user key, session expiry and inactive expiry
        cls.session_user_key = user_key
        cls.session_expiry = session_expiry
        cls.session_inactive = session_inactive

        # Set up lookup. Split a copy into self.lookup_id which has the ID, and
        # self.lookup which has gramex.data keywords.
        cls.lookup = None
        if lookup is not None:
            cls.lookup = lookup.copy()
            if isinstance(lookup, dict):
                cls.lookup_id = cls.lookup.pop('id', 'user')
            else:
                app_log.error(f'{cls.name}: lookup must be a dict, not {cls.lookup}')

        cls.rules = gramex.data.filter(**rules) if rules else gramex.data.pd.DataFrame()
        cls.rules.fillna(value='', inplace=True)

        # Set up prepare
        cls.auth_methods = {}
        if prepare is not None:
            cls.auth_methods['prepare'] = build_transform(
                conf={'function': prepare},
                vars={'handler': None, 'args': None},
                filename=f'url:{cls.name}:prepare',
                iter=False,
            )
        # Prepare recaptcha
        if recaptcha is not None:
            if 'key' not in recaptcha:
                app_log.error(f'{cls.name}: recaptcha.key missing')
            elif 'key' not in recaptcha:
                app_log.error(f'{cls.name}: recaptcha.secret missing')
            else:
                recaptcha.setdefault('action', 'login')
                cls.auth_methods['recaptcha'] = cls.check_recaptcha

        # Set up post-login actions
        cls.actions = []
        if action is not None:
            if not isinstance(action, list):
                action = [action]
            for conf in action:
                cls.actions.append(
                    build_transform(
                        conf, vars={'handler': None}, filename=f'url:{cls.name}:{conf.function}'
                    )
                )

    @coroutine
    def prepare(self):
        super(AuthHandler, self).prepare()
        if 'prepare' in self.auth_methods:
            result = yield gramex.service.threadpool.submit(
                self.auth_methods['prepare'], handler=self, args=self.args
            )
            if result is not None:
                self.args = result
        if 'recaptcha' in self.auth_methods:
            yield self.auth_methods['recaptcha'](self, self.kwargs.recaptcha)

    @staticmethod
    def update_user(_user_id, **kwargs):
        '''Update user login/logout event.'''
        info = _user_info.load(_user_id)
        info.update(kwargs)
        _user_info.dump(_user_id, info)
        return info

    @coroutine
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
                gramex.data.filter, args={self.lookup_id: [user['id']]}, **self.lookup
            )
            if len(users) > 0 and self.lookup_id in users.columns:
                # Update the user attributes with the non-null items in the looked up row
                user.update(
                    {
                        key: val
                        for key, val in users.iloc[0].items()
                        if not gramex.data.pd.isnull(val)
                    }
                )

        # Persist user attributes (e.g. refresh_token from Google auth.)
        # If new user object doesn't have anything from previous login, restore it.
        info = self.update_user(user[id], active='y', **user)
        merge(self.session[self.session_user_key], info, mode='setdefault')

        # If session_inactive: is specified, set expiry date on the session
        if self.session_inactive is not None:
            self.session['_i'] = self.session_inactive * 24 * 60 * 60

        # Apply rules to the user
        for _, rule in self.rules.iterrows():
            if fnmatch(user.get(rule['selector'], ''), rule['pattern']):
                user[rule['field']] = rule['value']

        # Run post-login events (e.g. ensure_single_session) specified in config
        for callback in self.actions:
            callback(self)
        self.log_user_event(event='login')

    @coroutine
    def fail_user(self, user, id):
        '''
        When user login fails, delay response. Delay = self.delay[# of failures].
        Or use the last value in the self.delay[] array.
        Return # failures
        '''
        failures = self.failed_logins[user[id]] = self.failed_logins[user[id]] + 1
        index = failures - 1
        delay = self.delay[index] if index < len(self.delay) else self.delay[-1]
        yield sleep(delay)

    def render_template(self, path, **kwargs):
        '''
        Like self.render(), but reloads updated templates.
        '''
        template = gramex.cache.open(path, 'template')
        namespace = self.get_template_namespace()
        namespace.update(kwargs)
        self.finish(template.generate(**namespace))

    @coroutine
    def check_recaptcha(self, conf):
        if self.request.method != 'POST':
            return
        token = self.get_argument('recaptcha', None)
        if token is None:
            raise HTTPError(FORBIDDEN, "'recaptcha' argument missing from POST")
        body = urlencode(
            {'secret': conf.secret, 'response': token, 'remoteip': self.request.remote_ip}
        )
        http = tornado.httpclient.AsyncHTTPClient()
        response = yield http.fetch(self._RECAPTCHA_VERIFY_URL, method='POST', body=body)
        result = json.loads(response.body)
        if not result['success']:
            raise HTTPError(FORBIDDEN, f'recaptcha failed: {", ".join(result["error-codes"])}')

    def authorize(self):
        '''AuthHandlers don't have authorization. They're meant to log users in.'''
        pass


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


class GoogleAuth(AuthHandler, GoogleOAuth2Mixin):
    @coroutine
    def get(self):
        self.settings[self._OAUTH_SETTINGS_KEY] = {
            'key': self.kwargs['key'],
            'secret': self.kwargs['secret'],
        }
        code = self.get_arg('code', '')
        if code:
            access = yield self.get_authenticated_user(redirect_uri=self.xredirect_uri, code=code)
            user = yield self.oauth2_request(
                'https://www.googleapis.com/oauth2/v1/userinfo',
                access_token=access['access_token'],
            )
            merge(user, access, mode='setdefault')
            yield self.set_user(user, id='email')
            self.session['google_access_token'] = access['access_token']
            self.redirect_next()
        else:
            self.save_redirect_page()
            # Ensure user-specified scope has 'profile' and 'email'
            scope = self.kwargs.get('scope', [])
            scope = scope if isinstance(scope, list) else [scope]
            scope = list(set(scope) | {'profile', 'email'})
            # Return the list
            yield self.authorize_redirect(
                redirect_uri=self.xredirect_uri,
                client_id=self.kwargs['key'],
                scope=scope,
                response_type='code',
                extra_params=self.kwargs.get('extra_params', {}),
            )

    @classmethod
    @coroutine
    def exchange_refresh_token(cls, user, refresh_token=None):
        '''
        Exchange the refresh token for the current user for a new access token.

        See https://developers.google.com/android-publisher/authorizatio#using_the_refresh_token

        The token is picked up from the persistent user info store. Developers can explicitly pass
        a refresh_token as well.

        Sample usage in a FunctionHandler coroutine::

            @tornado.gen.coroutine
            def refresh(handler):
                # Get the Google auth handler though which the current user logged in
                auth_handler = gramex.service.url['google-handler'].handler_class
                # Exchange refresh token for access token
                yield auth_handler.exchange_refresh_token(handler.current_user)

        It accepts the following parameters:

        :arg dict user: current user object, i.e. ``handler.current_user`` (read-only)
        :arg str refresh_token: optional. By default, the refresh token is picked up from
            ``handler.current_user.refresh_token``
        '''
        if refresh_token is None:
            if 'refresh_token' in user:
                refresh_token = user['refresh_token']
            else:
                raise HTTPError(FORBIDDEN, "No refresh_token provided")
        body = urlencode(
            {
                'grant_type': 'refresh_token',
                'client_id': cls.kwargs['key'],
                'client_secret': cls.kwargs['secret'],
                'refresh_token': refresh_token,
            }
        )
        http = tornado.httpclient.AsyncHTTPClient()
        response = yield http.fetch(cls._OAUTH_ACCESS_TOKEN_URL, method='POST', body=body)
        result = json.loads(response.body)
        # Update the current user info and persist it
        user.update(result)
        cls.update_user(user['email'], **result)


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

    @coroutine
    def get(self):
        self.save_redirect_page()
        self.render_template(self.template, error=None)

    @coroutine
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
