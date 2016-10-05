from __future__ import unicode_literals
import os
import csv
import six
import time
import uuid
import logging
import functools
import tornado.web
import tornado.gen
from tornado.auth import (GoogleOAuth2Mixin, FacebookGraphMixin, TwitterMixin,
                          urllib_parse, _auth_return_future)
from orderedattrdict import AttrDict
import gramex
from gramex.config import check_old_certs, app_log, objectpath
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
    def setup(cls, log={}, action=None, **kwargs):
        super(AuthHandler, cls).setup(**kwargs)
        gramex.service.threadpool.submit(check_old_certs)
        if log and hasattr(log, '__getitem__') and log.get('fields'):
            cls.log_fields = log['fields']
            cls.logger = logging.getLogger(log.get('logger', 'user'))
        else:
            cls.log_user_event = cls.noop
        cls.actions = []
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
        user['id'] = user[id]
        self.session['user'] = user
        for callback in self.actions:
            callback(self)
        self.log_user_event(event='login')


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
            self.set_user(user, id='id')
            self.redirect_next()
        else:
            self.save_redirect_page()
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
            'redirect_uri': redirect_uri,
            'code': code,
            'client_id': self.conf.kwargs['key'],
            'client_secret': self.conf.kwargs['secret'],
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
                client_id=self.conf.kwargs['key'],
                client_secret=self.conf.kwargs['secret'],
                code=self.get_argument('code'))
            self.set_user(user, id='id')
            self.redirect_next()
        else:
            self.save_redirect_page()
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
        if self.get_argument('oauth_token', None):
            user = yield self.get_authenticated_user()
            self.set_user(user, id='username')
            self.redirect_next()
        else:
            self.save_redirect_page()
            yield self.authenticate_redirect(callback_uri=self.request.protocol + "://" +
                                             self.request.host + self.request.uri)

    def _oauth_consumer_token(self):
        return dict(key=self.conf.kwargs['key'], secret=self.conf.kwargs['secret'])


class LDAPAuth(AuthHandler):
    @classmethod
    def setup(cls, **kwargs):
        super(LDAPAuth, cls).setup(**kwargs)
        cls.template = kwargs.get('template', _auth_template)

    def get(self):
        self.save_redirect_page()
        self.render(self.template, error=None)

    errors = {
        'conn': 'Connection error at {host}',
        'auth': 'Could not log in user',
        'search': 'Cannot get attributes for user on {host}',
    }

    def report_error(self, code, exc_info=False):
        error = self.errors[code].format(host=self.conf.kwargs.host, args=self.request.arguments)
        app_log.error('LDAP: ' + error, exc_info=exc_info)
        self.set_status(status_code=401)
        self.set_header('Auth-Error', code)
        self.render(self.template, error={'code': code, 'error': error})
        raise tornado.gen.Return()

    @tornado.gen.coroutine
    def post(self):
        import ldap3
        kwargs = self.conf.kwargs

        # First, bind the server with the provided user ID and password.
        q = {key: self.get_argument(key) for key in self.request.arguments}
        server = ldap3.Server(kwargs.host, kwargs.get('port'), kwargs.get('use_ssl', True))
        conn = ldap3.Connection(server, kwargs.user.format(**q), kwargs.password.format(**q))
        try:
            result = yield gramex.service.threadpool.submit(conn.bind)
            if result is False:
                self.report_error('auth', exc_info=False)
        except ldap3.LDAPException:
            self.report_error('conn', exc_info=True)

        # We now have a valid user. Get additional attributes
        user = {'dn': conn.user}
        try:
            result = yield gramex.service.threadpool.submit(
                conn.search, conn.user, '(objectClass=*)', attributes=ldap3.ALL_ATTRIBUTES)
        except ldap3.LDAPException:
            self.report_error('search', exc_info=True)
        if result and len(conn.entries) > 0:
            # Attributes may continue binary data. Get the result as JSON and then use the dict
            import json
            user.update(json.loads(conn.entries[0].entry_to_json()))

        self.set_user(user, id='dn')
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

    def get(self):
        self.save_redirect_page()
        self.render(self.template, error=None)

    def post(self):
        user = self.get_argument(self.user.arg)
        password = self.get_argument(self.password.arg)
        if self.credentials.get(user) == password:
            self.set_user({'user': user}, id='user')
            self.redirect_next()
        else:
            self.set_status(status_code=401)
            self.render(self.template, error={'code': 'auth', 'error': 'Cannot log in'})


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
            function: passlib.hash.sha256_crypt.encrypt         # Encryption function
            kwargs: {salt: 'secret-key'}                        # Salt key
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
                password, vars=AttrDict(content=None),
                filename='url:%s:encrypt' % (cls.name)))

    @classmethod
    def bind_to_db(cls):
        if not hasattr(cls, 'table'):
            from sqlalchemy import MetaData
            meta = MetaData(bind=cls.engine)
            cls.table = sa.Table(cls.tablename, meta, autoload=True, autoload_with=cls.engine)

    def get(self):
        self.save_redirect_page()
        template = self.template
        if self.forgot and self.forgot.key in self.request.arguments:
            template = self.forgot.template
        self.render(template, error=None)

    @tornado.gen.coroutine
    def post(self):
        # To access the table, we need to connect to the database. Doing that in
        # setup() is too early -- schedule or other methods may not have created
        # the table by then. So try here, and retry every request.
        self.bind_to_db()
        # TODO: if this bind does not work, report an error on connection

        if self.forgot and self.forgot.key in self.request.arguments:
            self.forgot_password()
        else:
            self.login()

    def login(self):
        user = self.get_argument(self.user.arg)
        password = self.get_argument(self.password.arg)
        for encrypt in self.encrypt:
            for result in encrypt(password):
                password = result

        from sqlalchemy import and_
        query = self.table.select().where(and_(
            self.table.c[self.user.column] == user,
            self.table.c[self.password.column] == password,
        ))
        result = self.engine.execute(query)
        user = result.fetchone()

        if user is not None:
            # Delete password from user object before storing it in the session
            user = dict(user)
            user.pop(self.password.column, None)
            self.set_user(user, id=self.user.column)
            self.redirect_next()
        else:
            self.set_status(status_code=401)
            self.render(self.template, error={
                'code': 'auth',
                'error': 'Cannot log in'
            })

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
                self.set_status(status_code=401)
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
                        for result in encrypt(password):
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
                    self.set_status(status_code=401)
                    error['error'] = 'Token expired'
            else:
                self.set_status(status_code=401)
                error['error'] = 'Invalid Token'
        self.render(template, error=error)

    @classmethod
    def setup_recover_db(cls):
        '''Set up the database that stores password recovery tokens'''
        from sqlalchemy import create_engine, MetaData
        # create database at GRAMEXDATA locastion
        path = os.path.join(gramex.variables.GRAMEXDATA, 'auth.recover.db')
        url = 'sqlite:///{}'.format(path)
        engine = create_engine(url, encoding=str('utf-8'))
        conn = engine.connect()
        conn.execute('CREATE TABLE IF NOT EXISTS users '
                     '(user TEXT, email TEXT, token TEXT, expire REAL)')
        meta = MetaData(bind=engine)
        user_table = sa.Table('users', meta, autoload=True, autoload_with=engine)
        return {'engine': engine, 'table': user_table}
