from __future__ import unicode_literals
import os
import csv
import six
import time
import uuid
import base64
import logging
import functools
import tornado.web
import tornado.gen
from socket import gethostname
from cachetools import TTLCache
from tornado.auth import (GoogleOAuth2Mixin, FacebookGraphMixin, TwitterMixin,
                          urllib_parse, _auth_return_future)
from collections import Counter
from orderedattrdict import AttrDict
import gramex
import gramex.cache
from gramex.http import UNAUTHORIZED
from gramex.config import check_old_certs, app_log, objectpath, str_utf8
from gramex.transforms import build_transform
from .basehandler import BaseHandler

_auth_template = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'auth.template.html')
_forgot_template = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'forgot.template.html')

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
    def setup(cls, log={}, action=None, delay=None, session_expiry=None, **kwargs):
        # Switch SSL certificates if required to access Google, etc
        gramex.service.threadpool.submit(check_old_certs)

        # Set up default redirection based on ?next=...
        if 'redirect' not in kwargs:
            kwargs['redirect'] = AttrDict([('query', 'next'), ('header', 'Referer')])
        super(AuthHandler, cls).setup(**kwargs)

        # Set up logging for login/logout events
        if log and hasattr(log, '__getitem__') and log.get('fields'):
            cls.log_fields = log['fields']
            cls.logger = logging.getLogger(log.get('logger', 'user'))
        else:
            cls.log_user_event = cls.noop
        cls.actions = []

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

        # Set up session expiry
        cls.session_expiry = session_expiry

        # Set up post-login actions
        if action is not None:
            if not isinstance(action, list):
                action = [action]
            for conf in action:
                cls.actions.append(build_transform(
                    conf, vars=AttrDict(handler=None),
                    filename='url:%s:%s' % (cls.name, conf.function)))

    def log_user_event(self, event, **kwargs):
        self.logger.info(csv_encode(
            [event] + [objectpath(self, f, '') for f in self.log_fields]))

    def noop(self, *args, **kwargs):
        pass

    def set_user(self, user, id):
        # When user logs in, change session ID and invalidate old session
        # https://www.owasp.org/index.php/Session_fixation
        self.get_session(expires_days=self.session_expiry, new=True)
        # The unique ID for a user varies across logins. For example, Google and
        # Facebook provide an "id", but for Twitter, it's "username". For LDAP,
        # it's "dn". Allow auth handlers to decide their own ID attribute and
        # store it as "id" for consistency. Logging depends on this, for example.
        user['id'] = user[id]
        self.session['user'] = user
        self.failed_logins[user[id]] = 0
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
        if self.redirects:
            self.save_redirect_page()
        for callback in self.actions:
            callback(self)
        self.session.pop('user', None)
        self.log_user_event(event='logout')
        if self.redirects:
            self.redirect_next()


class GoogleAuth(AuthHandler, GoogleOAuth2Mixin):
    @tornado.gen.coroutine
    def get(self):
        redirect_uri = '{0.protocol:s}://{0.host:s}{0.path:s}'.format(self.request)
        if self.get_argument('code', False):
            access = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'))
            user = yield self.oauth2_request(
                'https://www.googleapis.com/oauth2/v1/userinfo',
                access_token=access['access_token'])
            self.set_user(user, id='email')
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
        if self.get_argument('code', False):
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.kwargs['key'],
                client_secret=self.kwargs['secret'],
                code=self.get_argument('code'))
            self.set_user(user, id='id')
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
        if self.get_argument('oauth_token', None):
            user = yield self.get_authenticated_user()
            self.set_user(user, id='username')
            self.redirect_next()
        else:
            self.save_redirect_page()
            yield self.authenticate_redirect(callback_uri=self.request.protocol + "://" +
                                             self.request.host + self.request.uri)

    def _oauth_consumer_token(self):
        return dict(key=self.kwargs['key'], secret=self.kwargs['secret'])


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
        import json
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

        self.set_user(user, id='user')
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
        user = self.get_argument(self.user.arg)
        password = self.get_argument(self.password.arg)
        info = self.credentials.get(user)
        if info == password:
            self.set_user({'user': user}, id='user')
            self.redirect_next()
        elif hasattr(info, 'get') and info.get('password', None) == password:
            info.setdefault('user', user)
            self.set_user(info, id='user')
            self.redirect_next()
        else:
            yield self.fail_user({'user': user}, id='user')
            self.set_status(UNAUTHORIZED)
            self.render_template(self.template, error={'code': 'auth', 'error': 'Cannot log in'})


class DBAuth(SimpleAuth):
    '''
    The configuration (``kwargs``) for DBAuth looks like this::

        template: $YAMLPATH/auth.template.html  # Render the login form template
        url: sqlite:///$YAMLPATH/auth.db    # Pick up list of users from this sqlalchemy URL
        table: users                        # ... and this table
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
            email_text: 'This email is for {user}, {email}'

    The login flow is as follows:

    1. User visits the DBAuth page => shows template (with the user name and password inputs)
    2. User enters user name and password, and submits. Browser redirects with a POST request
    3. Application checks username and password. On match, redirects.
    4. On any error, shows template (with error)

    The forgot password flow is as follows:

    1. User visits ``?forgot`` => shows forgot password template (with the user name)
    2. User enters user name and submits. Browser redirects to ``POST ?forgot&user=...``
    3. Application generates a new password link (valid for ``minutes_to_expiry`` minutes).
    4. Application emails new password link to the email ID associated with user
    5. User is sent to ``?forgot=<token>`` => shows forgot password template (with password)
    6. User enters new password (twice) and submits => ``POST ?forgot=<token>&password=...``
    7. Application checks if token is valid. If yes, sets associated user's password and redirects
    8. On any error, shows forgot password template (with error)
    '''
    @classmethod
    def setup(cls, url, table, user, password, forgot=None, **kwargs):
        super(DBAuth, cls).setup(user=user, password=password, **kwargs)
        from sqlalchemy import create_engine
        cls.tablename, cls.forgot = table, forgot
        cls.engine = create_engine(url, **kwargs.get('parameters', {}))
        if cls.forgot:
            default_minutes_to_expiry = 15
            cls.forgot.setdefault('template', _forgot_template)
            cls.forgot.setdefault('key', 'forgot')
            cls.forgot.setdefault('arg', 'email')
            cls.forgot.setdefault('email_column', 'email')
            cls.forgot.setdefault('minutes_to_expiry', default_minutes_to_expiry)
            cls.forgot.setdefault('email_subject', 'Password reset')
            cls.forgot.setdefault(
                'email_text', 'Visit {reset_url} to reset password for user {user} ({email})')
            cls.recover = cls.setup_recover_db()
            # TODO: default email_from to the first available email service
        cls.encrypt = []
        if 'function' in password:
            cls.encrypt.append(build_transform(
                password, vars=AttrDict(handler=None, content=None),
                filename='url:%s:encrypt' % (cls.name)))

    @classmethod
    def bind_to_db(cls):
        if not hasattr(cls, 'table'):
            from sqlalchemy import MetaData, Table
            meta = MetaData(bind=cls.engine)
            cls.table = Table(cls.tablename, meta, autoload=True, autoload_with=cls.engine)

    def get(self):
        self.save_redirect_page()
        template = self.template
        if self.forgot and self.forgot.key in self.args:
            template = self.forgot.template
        self.render_template(template, error=None)

    @tornado.gen.coroutine
    def post(self):
        # To access the table, we need to connect to the database. Doing that in
        # setup() is too early -- schedule or other methods may not have created
        # the table by then. So try here, and retry every request.
        self.bind_to_db()
        # TODO: if this bind does not work, report an error on connection

        if self.forgot and self.forgot.key in self.args:
            self.forgot_password()
        else:
            yield self.login()

    @tornado.gen.coroutine
    def login(self):
        user = self.get_argument(self.user.arg)
        password = self.get_argument(self.password.arg)
        for encrypt in self.encrypt:
            for result in encrypt(handler=self, content=password):
                password = result

        from sqlalchemy import and_
        query = self.table.select().where(and_(
            self.table.c[self.user.column] == user,
            self.table.c[self.password.column] == password,
        ))
        result = self.engine.execute(query)
        user_obj = result.fetchone()

        if user_obj is not None:
            # Delete password from user object before storing it in the session
            user_obj = dict(user_obj)
            user_obj.pop(self.password.column, None)
            self.set_user(user_obj, id=self.user.column)
            self.redirect_next()
        else:
            yield self.fail_user({'user': user}, 'user')
            self.set_status(UNAUTHORIZED)
            self.render_template(self.template, error={'code': 'auth', 'error': 'Cannot log in'})

    def forgot_password(self):
        template = self.forgot.template
        error = {'code': 'auth'}
        forgot_key = self.get_argument(self.forgot.key)

        # Step 1: user submits their user ID / email via POST ?forgot&user=...
        if not forgot_key:
            # Get the user based on the user ID or email ID (in that priority)
            forgot_user = self.get_argument(self.user.arg, None)
            forgot_email = self.get_argument(self.forgot.arg, None)
            if forgot_user:
                query = self.table.c[self.user.column] == forgot_user
            else:
                query = self.table.c[self.forgot.email_column] == forgot_email
            result = self.engine.execute(self.table.select().where(query))
            user = result.fetchone()
            email_column = self.forgot.get('email_column', 'email')

            # If a mathing user exists in the database
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
                self.recover['engine'].execute(
                    self.recover['table'].insert(), values)
                # send password reset mail to user
                mailer = gramex.service.email[self.forgot.email_from]
                reset_url = self.request.protocol + '://' + self.request.host + self.request.path
                reset_url += '?' + urllib_parse.urlencode({self.forgot.key: token})
                # TODO: after the email is sent, if there's an exception, log the exception
                gramex.service.threadpool.submit(
                    mailer.mail,
                    to=user[email_column],
                    subject=self.forgot.email_subject.format(reset_url=reset_url, **user),
                    body=self.forgot.email_text.format(reset_url=reset_url, **user))
                error = {}                          # Render at the end with no errors
            # If no user matches the user ID or email ID
            else:
                self.set_status(UNAUTHORIZED)
                if user is None:
                    error['error'] = 'No user matching %s found' % (forgot_user or forgot_email)
                elif not user[email_column]:
                    error['error'] = 'No email matching %s found' % (forgot_user or forgot_email)

        # Step 2: User clicks on email, submits new password via POST ?forgot=<token>&password=...
        else:
            where = self.recover['table'].c['token'] == forgot_key
            result = self.recover['engine'].execute(
                self.recover['table'].select().where(where))
            row = result.fetchone()
            # if system generated token in database
            if row is not None:
                # if token is not expired
                if row['expire'] > time.time():
                    password = self.get_argument(self.password.arg)
                    for encrypt in self.encrypt:
                        for result in encrypt(handler=self, content=password):
                            password = result
                    # update password in database
                    values = {
                        self.user.column: row['user'],
                        self.password.column: password}
                    query = self.table.update().where(
                        self.table.c[self.user.column] == row['user']
                    ).values(values)
                    self.engine.execute(query)
                    self.recover['engine'].execute(
                        self.recover['table'].delete(where))
                    error = {}
                else:
                    self.set_status(UNAUTHORIZED)
                    error['error'] = 'Token expired'
            else:
                self.set_status(UNAUTHORIZED)
                error['error'] = 'Invalid Token'
        self.render_template(template, error=error)

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

        self.set_user(user, 'id')
        self.redirect_next()
