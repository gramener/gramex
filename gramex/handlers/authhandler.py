import os
import csv
import six
import json
import time
import uuid
import logging
import tornado.escape
import tornado.httpclient
from tornado.auth import GoogleOAuth2Mixin
from tornado.gen import coroutine, sleep
from tornado.web import HTTPError
from collections import Counter
from orderedattrdict import AttrDict
import gramex
import gramex.cache
from gramex.http import UNAUTHORIZED, FORBIDDEN
from gramex.config import check_old_certs, app_log, objectpath, str_utf8
from gramex.transforms import build_transform
from .basehandler import BaseHandler, build_log_info

_folder = os.path.dirname(os.path.abspath(__file__))
_auth_template = os.path.join(_folder, 'auth.template.html')
_user_info_path = os.path.join(gramex.variables.GRAMEXDATA, 'auth.user.db')
_user_info = gramex.cache.SQLiteStore(_user_info_path, table='user')

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


class AuthHandler(BaseHandler):
    '''The parent handler for all Auth handlers.'''
    _RECAPTCHA_VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'

    @classmethod
    def setup_default_kwargs(cls):
        super(AuthHandler, cls).setup_default_kwargs()
        # Warn and ignore if AuthHandler sets an auth:
        conf = cls.conf.setdefault('kwargs', {})
        if 'auth' in conf:
            conf.pop('auth')
            app_log.warning('%s: Ignoring auth on AuthHandler', cls.name)

    @classmethod
    def setup(cls, prepare=None, action=None, delay=None, session_expiry=None,
              session_inactive=None, user_key='user', lookup=None, recaptcha=None, **kwargs):
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

        # Set up lookup. Split a copy into self.lookup_id which has the ID, and
        # self.lookup which has gramex.data keywords.
        cls.lookup = None
        if lookup is not None:
            cls.lookup = lookup.copy()
            if isinstance(lookup, dict):
                cls.lookup_id = cls.lookup.pop('id', 'user')
            else:
                app_log.error('%s: lookup must be a dict, not %s', cls.name, cls.lookup)

        # Set up prepare
        cls.auth_methods = {}
        if prepare is not None:
            cls.auth_methods['prepare'] = build_transform(
                conf={'function': prepare},
                vars={'handler': None, 'args': None},
                filename='url:%s:prepare' % cls.name,
                iter=False)
        # Prepare recaptcha
        if recaptcha is not None:
            if 'key' not in recaptcha:
                app_log.error('%s: recaptcha.key missing', cls.name)
            elif 'key' not in recaptcha:
                app_log.error('%s: recaptcha.secret missing', cls.name)
            else:
                recaptcha.setdefault('action', 'login')
                cls.auth_methods['recaptcha'] = cls.check_recaptcha

        # Set up post-login actions
        cls.actions = []
        if action is not None:
            if not isinstance(action, list):
                action = [action]
            for conf in action:
                cls.actions.append(build_transform(
                    conf, vars=AttrDict(handler=None),
                    filename='url:%s:%s' % (cls.name, conf.function)))

    @coroutine
    def prepare(self):
        super(AuthHandler, self).prepare()
        if 'prepare' in self.auth_methods:
            result = yield gramex.service.threadpool.submit(
                self.auth_methods['prepare'], handler=self, args=self.args)
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
        body = six.moves.urllib_parse.urlencode({
            'secret': conf.secret,
            'response': token,
            'remoteip': self.request.remote_ip
        })
        http = tornado.httpclient.AsyncHTTPClient()
        response = yield http.fetch(self._RECAPTCHA_VERIFY_URL, method='POST', body=body)
        result = json.loads(response.body)
        if not result['success']:
            raise HTTPError(FORBIDDEN, 'recaptcha failed: %s' % ', '.join(result['error-codes']))


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
            'secret': self.kwargs['secret']
        }
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


class OTP(object):
    '''
    OTP: One-time password. Also used for password recovery
    '''
    def __init__(self, size=None):
        '''
        Set up the database that stores password recovery tokens.
        ``size`` is the length of the OTP in characters. Defaults to the
        full hashing string
        '''
        self.size = size
        # create database at GRAMEXDATA
        path = os.path.join(gramex.variables.GRAMEXDATA, 'auth.recover.db')
        url = 'sqlite:///{}'.format(path)
        self.engine = gramex.data.create_engine(url, encoding=str_utf8)
        conn = self.engine.connect()
        conn.execute('CREATE TABLE IF NOT EXISTS users '
                     '(user TEXT, email TEXT, token TEXT, expire REAL)')
        self.table = gramex.data.get_table(self.engine, 'users')

    def token(self, user, email, expire):
        '''Generate a one-tie token, store it in the recovery database, and return it'''
        token = uuid.uuid4().hex[:self.size]
        query = self.table.insert().values({
            'user': user, 'email': email, 'token': token, 'expire': expire,
        })
        self.engine.execute(query)
        return token

    def pop(self, token):
        '''Return the row matching the token, and deletes it from the list'''
        where = self.table.c['token'] == token
        query = self.table.select().where(where)
        result = self.engine.execute(query)
        if result.returns_rows:
            row = result.fetchone()
            if row is not None:
                self.engine.execute(self.table.delete(where))
                if row['expire'] >= time.time():
                    return row
        return None


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
