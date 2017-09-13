from __future__ import unicode_literals

import io
import os
import csv
import six
import json
import time
import atexit
import mimetypes
import traceback
import tornado.gen
import gramex.cache
from textwrap import dedent
from binascii import b2a_base64, hexlify
from orderedattrdict import AttrDict, DefaultAttrDict
from six.moves.urllib_parse import urlparse, urlsplit, urljoin, urlencode
from tornado.log import access_log
from tornado.web import RequestHandler, HTTPError
from tornado.websocket import WebSocketHandler
from gramex import conf, __version__
from gramex.config import merge, objectpath, app_log, CustomJSONDecoder, CustomJSONEncoder
from gramex.transforms import build_transform
from gramex.http import UNAUTHORIZED, FORBIDDEN, BAD_REQUEST

server_header = 'Gramex/%s' % __version__
session_store_cache = {}


class BaseMixin(object):
    @classmethod
    def setup(cls, transform={}, redirect={}, auth=None, log={}, set_xsrf=None,
              error=None, xsrf_cookies=None, **kwargs):
        '''
        One-time setup for all request handlers. This is called only when
        gramex.yaml is parsed / changed.
        '''
        cls._on_init_methods = []
        cls._on_finish_methods = []

        # handler.kwargs returns kwargs with BaseHandler kwargs removed
        cls.kwargs = AttrDict(kwargs)
        cls.setup_default_kwargs()

        cls.setup_transform(transform)
        cls.setup_redirect(redirect)
        # Note: call setup_session before setup_auth to ensure that
        # override_user is run before authorize
        cls.setup_session(conf.app.get('session'))
        cls.setup_auth(auth)
        cls.setup_log(log or objectpath(conf, 'handlers.BaseHandler.log'))
        cls.setup_error(error)
        cls.setup_xsrf(xsrf_cookies)
        cls._set_xsrf = set_xsrf

        # app.settings.debug enables debugging exceptions using pdb
        if conf.app.settings.get('debug', False):
            cls.log_exception = cls.debug_exception

    @classmethod
    def setup_default_kwargs(cls):
        '''Use configs under handlers.<ClassName>.* as the default for kwargs'''
        update = objectpath(conf, 'handlers.' + cls.conf.handler, {})
        merge(cls.conf.setdefault('kwargs', {}), update, mode='setdefault')
        merge(cls.kwargs, update, mode='setdefault')

    @classmethod
    def setup_transform(cls, transform):
        cls.transform = {}
        for pattern, trans in transform.items():
            cls.transform[pattern] = {
                'function': build_transform(
                    trans, vars=AttrDict((('content', None), ('handler', None))),
                    filename='url:%s' % cls.name),
                'headers': trans.get('headers', {}),
                'encoding': trans.get('encoding'),
            }

    @staticmethod
    def _purge(data):
        '''
        Clear any expired session keys based on _t.
        setup_session makes the session store call this purge method.
        Until v1.20 (31 Jul 2017) no _t keys were set.
        TODO: In a release after 30 Sep 2017, clear sessions that lack an _t
        '''
        now = time.time()
        for key in list(data.keys()):
            val = data[key]
            if val is None or (isinstance(val, dict) and val.get('_t', 9999999999) < now):
                del data[key]

    @classmethod
    def setup_session(cls, session_conf):
        '''handler.session returns the session object. It is saved on finish.'''
        if session_conf is None:
            return
        key = store_type, store_path = session_conf.get('type'), session_conf.get('path')
        flush = session_conf.get('flush')
        if key in session_store_cache:
            pass
        elif store_type == 'memory':
            session_store_cache[key] = KeyStore(store_path, flush=flush, purge=cls._purge)
        elif store_type == 'json':
            session_store_cache[key] = JSONStore(store_path, flush=flush, purge=cls._purge)
        elif store_type == 'hdf5':
            session_store_cache[key] = HDF5Store(store_path, flush=flush, purge=cls._purge)
        else:
            raise NotImplementedError('Session type: %s not implemented' % store_type)
        cls._session_store = session_store_cache[key]
        cls.session = property(cls.get_session)
        cls._session_days = session_conf.get('expiry')
        cls._on_finish_methods.append(cls.save_session)
        cls._on_init_methods.append(cls.override_user)

        if 'private_key' in session_conf:
            keyfile = session_conf['private_key']
            if not os.path.exists(keyfile):
                app_log.error('app.session.private_key: %s missing', keyfile)
                return
            with open(keyfile, 'rb') as handle:
                keytext = handle.read()
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives.asymmetric import padding
            from base64 import b64decode
            key = serialization.load_pem_private_key(
                keytext, password=None, backend=default_backend())
            pad = padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None)
            cls._session_decrypt = lambda cls, s: json.loads(key.decrypt(b64decode(s), pad))

    @classmethod
    def setup_redirect(cls, redirect):
        '''
        Any handler can have a ``redirect:`` kwarg that looks like this::

            redirect:
                query: next         # If the URL has a ?next=..., redirect to that page next
                header: X-Next      # Else if the header has an X-Next=... redirect to that
                url: ...            # Else redirect to this URL

        Only these 3 keys are allowed. All are optional, and checked in the
        order specified. So, for example::

            redirect:
                header: X-Next      # Checks the X-Next header first
                query: next         # If it's missing, uses the ?next=

        You can also specify a string for redirect. ``redirect: ...`` is the same
        as ``redirect: {url: ...}``.

        When any BaseHandler subclass calls ``self.save_redirect_page()``, it
        stores the redirect URL in ``session['_next_url']``. The URL is
        calculated relative to the handler's URL.

        After that, when the subclass calls ``self.redirect_next()``, it
        redirects to ``session['_next_url']`` and clears the value. (If the
        ``_next_url`` was not stored, we redirect to the home page ``/``.)

        Only some handlers implement redirection. But they all implement it in
        this same consistent way.
        '''
        # Ensure that redirect is a dictionary before proceeding.
        if isinstance(redirect, six.string_types):
            redirect = {'url': redirect}
        if not isinstance(redirect, dict):
            app_log.error('url:%s.redirect must be a URL or a dict, not %s',
                          cls.name, repr(redirect))
            return

        cls.redirects = []
        add = cls.redirects.append
        for key, value in redirect.items():
            if key == 'query':
                add(lambda h, v=value: h.get_argument(v, None))
            elif key == 'header':
                add(lambda h, v=value: h.request.headers.get(v))
            elif key == 'url':
                add(lambda h, v=value: v)

        # redirect.external=False disallows external URLs
        if not redirect.get('external', False):
            def no_external(method):
                def redirect_method(handler):
                    next_uri = method(handler)
                    if next_uri is not None:
                        target = urlparse(next_uri)
                        if not target.scheme and not target.netloc:
                            return next_uri
                        req = handler.request
                        if req.protocol == target.scheme and req.host == target.netloc:
                            return next_uri
                        app_log.error('Not redirecting to external url: %s', next_uri)
                return redirect_method
            cls.redirects = [no_external(method) for method in cls.redirects]

    @classmethod
    def setup_auth(cls, auth):
        # auth: if there's no auth: in handler, default to app.auth
        if auth is None:
            auth = conf.app.get('auth')
        # Treat True as an empty dict, i.e. auth: {}
        if auth is True:
            auth = AttrDict()
        # If auth is False or None, ignore it. Otherwise, process the auth
        if auth is not None and auth is not False:
            cls._login_url = auth.get('login_url')
            cls._on_init_methods.append(cls.authorize)
            cls.permissions = []
            # Add check for condition
            if auth.get('condition'):
                cls.permissions.append(
                    build_transform(auth['condition'], vars=AttrDict(handler=None),
                                    filename='url:%s.auth.permission' % cls.name))
            # Add check for membership
            memberships = auth.get('membership', [])
            if not isinstance(memberships, list):
                memberships = [memberships]
            if len(memberships):
                cls.permissions.append(check_membership(memberships))

    @classmethod
    def setup_log(cls, log):
        try:
            cls.log_request = log_method(log)
        except (ValueError, OSError):
            app_log.log_exception('url:%s: cannot set up log: %r', cls.name, log)

    @classmethod
    def setup_error(cls, error):
        '''
        Sample configuration::

            error:
                404:
                    path: template.json         # Use a template
                    autoescape: false           # with no autoescape
                    whitespace: single          # as a single line
                    headers:
                        Content-Type: application/json
                500:
                    function: module.fn
                    args: [=status_code, =kwargs, =handler]
        '''
        if not error:
            return
        if not isinstance(error, dict):
            return app_log.error('url:%s.error is not a dict', cls.name)
        # Compile all errors handlers
        cls.error = {}
        for error_code, error_config in error.items():
            try:
                error_code = int(error_code)
                assert 100 <= error_code <= 1000
            except (ValueError, AssertionError):
                app_log.error('url.%s.error code %s is not a number (100 - 1000)',
                              cls.name, error_code)
                continue
            if not isinstance(error_config, dict):
                return app_log.error('url:%s.error.%d is not a dict', cls.name, error_code)
            if 'path' in error_config:
                encoding = error_config.get('encoding', 'utf-8')
                template_kwargs = {}
                if 'autoescape' in error_config:
                    if not error_config['autoescape']:
                        template_kwargs['autoescape'] = None
                    else:
                        app_log.error('url:%s.error.%d.autoescape can only be false',
                                      cls.name, error_code)
                if 'whitespace' in error_config:
                    template_kwargs['whitespace'] = error_config['whitespace']

                def _error_function(*args, **kwargs):
                    tmpl = gramex.cache.open(error_config['path'], 'template', autoescape=None)
                    return tmpl.generate(*args, **kwargs)

                cls.error[error_code] = {'function': _error_function}
                mime_type, encoding = mimetypes.guess_type(error_config['path'], strict=False)
                if mime_type:
                    error_config.setdefault('headers', {}).setdefault('Content-Type', mime_type)
            elif 'function' in error_config:
                cls.error[error_code] = {'function': build_transform(
                    error_config,
                    vars=AttrDict((('status_code', None), ('kwargs', None), ('handler', None))),
                    filename='url:%s.error.%d' % (cls.name, error_code)
                )}
            else:
                app_log.error('url.%s.error.%d must have a path or function key',
                              cls.name, error_code)
        if error_code in cls.error:
            cls.error[error_code]['conf'] = error_config
        cls._write_error, cls.write_error = cls.write_error, cls._write_custom_error

    @classmethod
    def setup_xsrf(cls, xsrf_cookies):
        '''
        Sample configuration::

            xsrf_cookies: false         # Disables xsrf_cookies
            xsrf_cookies: true          # or anything other than false keeps it enabled
        '''
        if xsrf_cookies is False:
            cls.check_xsrf_cookie = cls.noop

    def noop(self):
        '''Does nothing. Used when overriding functions or providing a dummy operation'''
        pass

    def save_redirect_page(self):
        '''
        Loop through all redirect: methods and save the first available redirect
        page against the session. Defaults to previously set value, else ``/``.

        See :py:func:`setup_redirect`
        '''
        for method in self.redirects:
            next_url = method(self)
            if next_url:
                self.session['_next_url'] = urljoin(self.request.uri, next_url)
                return
        self.session.setdefault('_next_url', '/')

    def redirect_next(self):
        '''
        Redirect the user ``session['_next_url']``. If it does not exist,
        redirect to the home page ``/``.

        See :py:func:`setup_redirect`
        '''
        self.redirect(self.session.pop('_next_url', '/'))

    @tornado.gen.coroutine
    def _cached_get(self, *args, **kwargs):
        cached = self.cachefile.get()
        if cached is not None:
            self.set_status(cached['status'])
            self._write_headers(cached['headers'])
            self.write(cached['body'])
        else:
            self.cachefile.wrap(self)
            yield self.original_get(*args, **kwargs)

    def _write_headers(self, headers):
        '''Write headers from a list of pairs that may be duplicated'''
        headers_written = set()
        for name, value in headers:
            # If value is explicitly False or None, clear header.
            # This gives a way to clear pre-set headers like the Server header
            if value is False or value is None:
                self.clear_header(name)
            elif name in headers_written:
                self.add_header(name, value)
            else:
                self.set_header(name, value)
                headers_written.add(name)

    def debug_exception(self, typ, value, tb):
        super(BaseHandler, self).log_exception(typ, value, tb)
        import ipdb as pdb
        pdb.post_mortem(tb)

    def _write_custom_error(self, status_code, **kwargs):
        if status_code in self.error:
            try:
                result = self.error[status_code]['function'](
                    status_code=status_code, kwargs=kwargs, handler=self)
                headers = self.error[status_code].get('conf', {}).get('headers', {})
                self._write_headers(headers.items())
                # result may be a generator / list from build_transform,
                # or a str/bytes/unicode from Template.generate. Handle both
                if isinstance(result, (six.string_types, six.binary_type)):
                    self.write(result)
                else:
                    for item in result:
                        self.write(item)
                return
            except Exception:
                app_log.exception('url:%s.error.%d error handler raised an exception:',
                                  self.name, status_code)
        # If error was not written, use the default error
        self._write_error(status_code, **kwargs)

    @property
    def session(self):
        '''
        By default, session is not implemented. You need to specify a
        ``session:`` section in ``gramex.yaml`` to activate it. It is replaced by
        the ``get_session`` method as a property.
        '''
        raise NotImplementedError('Specify a session: section in gramex.yaml')

    def _set_new_session_id(self, expires_days):
        '''Sets a new random session ID as the sid: cookie. Returns a bytes object'''
        session_id = b2a_base64(os.urandom(24))[:-1]
        kwargs = dict(httponly=True, expires_days=expires_days)
        # Use Secure cookies on HTTPS to prevent leakage into HTTP
        if self.request.protocol == 'https':
            kwargs['secure'] = True
        # Websockets cannot set cookies. They raise a RuntimeError. Ignore those.
        try:
            self.set_secure_cookie('sid', session_id, **kwargs)
        except RuntimeError:
            pass
        return session_id

    def get_session(self, expires_days=None, new=False):
        '''
        Return the session object for the cookie "sid" value. If no "sid" cookie
        exists, set up a new one. If no session object exists for the sid,
        create it. By default, the session object contains a "id" holding the
        "sid" value.

        The session is a dict. You must ensure that it is JSON serializable.

        ``new=`` creates a new session to avoid session fixation.
        https://www.owasp.org/index.php/Session_fixation.
        :py:func:`gramex.handlers.authhandler.AuthHandler.set_user` uses it.
        When the user logs in. If no old session exists, it returns a new session
        object. If an old session exists, it creates a new session "sid" and new
        session object, copying all old contents, but updates the "id" and expiry
        (_t).
        '''
        if expires_days is None:
            expires_days = self._session_days
        created_new_sid = False
        if getattr(self, '_session', None) is None:
            # Populate self._session based on the sid. If there's no sid cookie,
            # generate one and create an associated session object
            session_id = self.get_secure_cookie('sid', max_age_days=9999999)
            # If there's no session id cookie "sid", create a random 32-char cookie
            if session_id is None:
                session_id = self._set_new_session_id(expires_days)
                created_new_sid = True
            # Convert bytes session to unicode before using
            session_id = session_id.decode('ascii')
            # If there's no stored session associated with it, create it
            expires = time.time() + expires_days * 24 * 60 * 60
            self._session = self._session_store.load(session_id, {'_t': expires})
            # Overwrite id to the session ID even if a handler has changed it
            self._session['id'] = session_id
        # At this point, the "sid" cookie and self._session exist and are synced

        if new and not created_new_sid:
            old_sid = self._session['id']
            new_sid = self._set_new_session_id(expires_days).decode('ascii')
            # Update expiry and new SID on session
            self._session.update(id=new_sid, _t=time.time() + expires_days * 24 * 60 * 60)
            # Delete old contents. No _t also means expired
            self._session_store.dump(old_sid, {})

        return self._session

    def save_session(self):
        '''Persist the session object as a JSON'''
        if getattr(self, '_session', None) is not None:
            self._session_store.dump(self._session['id'], self._session)

    def otp(self, expire=60):
        '''
        Return a one-time password valid for ``expire`` seconds. When the
        X-Gramex-OTP header
        '''
        user = self.current_user
        if not user:
            raise HTTPError(UNAUTHORIZED)
        nbits = 16
        otp = hexlify(os.urandom(nbits)).decode('ascii')
        self._session_store.dump('otp:' + otp, {'user': user, '_t': time.time() + expire})
        return otp

    def override_user(self):
        '''
        Use ``X-Gramex-User`` HTTP header to override current user for the session.
        Use ``X-Gramex-OTP`` HTTP header to set user based on OTP.
        ``?gramex-otp=`` is a synonym for X-Gramex-OTP.
        '''
        headers = self.request.headers
        cipher = headers.get('X-Gramex-User')
        if cipher:
            try:
                user = self._session_decrypt(cipher)
            except Exception:
                log_message = '%s: invalid X-Gramex-User: %s' % (self.name, cipher)
                raise HTTPError(BAD_REQUEST, log_message)
            else:
                app_log.debug('%s: Overriding user to %r', self.name, user)
                self.session['user'] = user
                return
        otp = headers.get('X-Gramex-OTP') or self.get_argument('gramex-otp', None)
        if otp:
            otp_data = self._session_store.load('otp:' + otp, None)
            if not isinstance(otp_data, dict) or '_t' not in otp_data or 'user' not in otp_data:
                log_message = '%s: invalid X-Gramex-OTP: %s' % (self.name, otp)
                raise HTTPError(BAD_REQUEST, log_message)
            elif otp_data['_t'] < time.time():
                log_message = '%s: expired X-Gramex-OTP: %s' % (self.name, otp)
                raise HTTPError(BAD_REQUEST, log_message)
            self._session_store.dump('otp:' + otp, None)
            self.session['user'] = otp_data['user']


class BaseHandler(RequestHandler, BaseMixin):
    '''
    BaseHandler provides auth, caching and other services common to all request
    handlers. All RequestHandlers must inherit from BaseHandler.
    '''
    def initialize(self, **kwargs):
        # self.request.arguments does not handle unicode keys well.
        # In Py2, it returns a str (not unicode). In Py3, it returns latin-1 unicode.
        # Convert this to proper unicode using UTF-8 and store in self.args
        self.args = {}
        for k in self.request.arguments:
            key = (k if isinstance(k, six.binary_type) else k.encode('latin-1')).decode('utf-8')
            self.args[key] = self.get_arguments(k)

        self._session, self._session_json = None, 'null'
        if self.cache:
            self.cachefile = self.cache()
            self.original_get = self.get
            self.get = self._cached_get
        if self._set_xsrf:
            self.xsrf_token

        # Set the method to the ?x-http-method-overrride argument or the
        # X-HTTP-Method-Override header if they exist
        if 'x-http-method-override' in self.args:
            self.request.method = self.args.pop('x-http-method-override')[0]
        elif 'X-HTTP-Method-Override' in self.request.headers:
            self.request.method = self.request.headers['X-HTTP-Method-Override']

    def prepare(self):
        for method in self._on_init_methods:
            method(self)

    def set_default_headers(self):
        # Only set BaseHandler headers.
        # Don't set headers for the specific class. Those are overrides handled
        # by the respective classes, not the default headers.
        headers = [('Server', server_header)]
        headers += list(objectpath(conf, 'handlers.BaseHandler.headers', {}).items())
        self._write_headers(headers)

    def on_finish(self):
        # Loop through class-level callbacks
        for callback in self._on_finish_methods:
            callback(self)

    def get_current_user(self):
        '''Return the ``user`` key from the session as an AttrDict if it exists.'''
        result = self.session.get('user')
        return AttrDict(result) if isinstance(result, dict) else result

    def log_exception(self, typ, value, tb):
        '''Store the exception value for logging'''
        super(BaseHandler, self).log_exception(typ, value, tb)
        # _exception is stored for use by log_request. Sample error string:
        # ZeroDivisionError: integer division or modulo by zero
        self._exception = traceback.format_exception_only(typ, value)[0].strip()

    def authorize(self):
        # If the user isn't logged in, redirect to login URL or send a 401
        if not self.current_user:
            if self.request.method in ('GET', 'HEAD'):
                url = self._login_url or self.get_login_url()
                if '?' not in url:
                    if urlsplit(url).scheme:
                        # if login url is absolute, make next absolute too
                        next_url = self.request.full_url()
                    else:
                        next_url = self.request.uri
                    url += '?' + urlencode(dict(next=next_url))
                self.redirect(url)
                return
            raise HTTPError(UNAUTHORIZED)

        # If the user doesn't have permissions, show 403 (with template)
        for permit_generator in self.permissions:
            for result in permit_generator(self):
                if not result:
                    template = self.conf.kwargs.auth.get('template')
                    if template:
                        self.set_status(FORBIDDEN)
                        self.render(template)
                    raise HTTPError(FORBIDDEN)

    def argparse(self, *args, **kwargs):
        '''
        Parse URL query parameters and return an AttrDict. For example::

            args = handler.argparse('x', 'y')
            args.x      # is the last value of ?x=value
            args.y      # is the last value of ?y=value

        A missing ``?x=`` or ``?y=`` raises a HTTP 400 error mentioning the
        missing key.

        For optional arguments, use::

            args = handler.argparse(z={'default': ''})
            args.z      # returns '' if ?z= is missing

        You can convert the value to a type::

            args = handler.argparse(limit={'type': int, 'default': 100})
            args.limit      # returns ?limit= as an integer

        You can restrict the choice of values. If the query parameter is not in
        choices, we raise a HTTP 400 error mentioning the invalid key & value::

            args = handler.argparse(gender={'choices': ['M', 'F']})
            args.gender      # returns ?gender= which will be 'M' or 'F'

        You can retrieve multiple values as a list::

            args = handler.argparse(cols={'nargs': '*', 'default': []})
            args.cols       # returns an array with all ?col= values

        ``type:`` conversion and ``choices:`` apply to each value in the list.

        To return all arguments as a list, pass ``list`` as the first parameter::

            args = handler.argparse(list, 'x', 'y')
            args.x      # ?x=1 sets args.x to ['1'], not '1'
            args.y      # Similarly for ?y=1

        To handle unicode arguments and return all arguments as ``str`` or
        ``unicode`` or ``bytes``, pass the type as the first parameter::

            args = handler.argparse(str, 'x', 'y')
            args = handler.argparse(bytes, 'x', 'y')
            args = handler.argparse(unicode, 'x', 'y')

        By default, all arguments are added as str in PY3 and unicode in PY2.

        There are the full list of parameters you can pass to each keyword
        argument:

        - name: Name of the URL query parameter to read. Defaults to the key
        - required: Whether or not the query parameter may be omitted
        - default: The value produced if the argument is missing. Implies required=False
        - nargs: The number of parameters that should be returned. '*' or '+'
          return all values as a list.
        - type: Python type to which the parameter should be converted (e.g. `int`)
        - choices: A container of the allowable values for the argument (after type conversion)

        You can combine all these options. For example::

            args = handler.argparse(
                'name',                         # Raise error if ?name= is missing
                department={'name': 'dept'},    # ?dept= is mapped to args.department
                org={'default': 'Gramener'},    # If ?org= is missing, defaults to Gramener
                age={'type': int},              # Convert ?age= to an integer
                married={'type': bool},         # Convert ?married to a boolean
                alias={'nargs': '*'},           # Convert all ?alias= to a list
                gender={'choices': ['M', 'F']}, # Raise error if gender is not M or F
            )
        '''
        result = AttrDict()

        args_type = six.text_type
        if len(args) > 0 and args[0] in (six.text_type, six.binary_type, list, None):
            args_type, args = args[0], args[1:]

        for key in args:
            result[key] = self.get_argument(key, None)
            if result[key] is None:
                raise HTTPError(BAD_REQUEST, reason='%s: missing ?%s=' % (key, key))
        for key, config in kwargs.items():
            name = config.get('name', key)
            val = self.args.get(name, [])

            # default: set if query is missing
            # required: check if query is defined at all
            if len(val) == 0:
                if 'default' in config:
                    result[key] = config['default']
                    continue
                if config.get('required', False):
                    raise HTTPError(BAD_REQUEST, reason='%s: missing ?%s=' % (key, name))

            # nargs: select the subset of items
            nargs = config.get('nargs', None)
            if isinstance(nargs, int):
                val = val[:nargs]
                if len(val) < nargs:
                    val += [''] * (nargs - len(val))
            elif nargs not in ('*', '+', None):
                raise ValueError('%s: invalid nargs %s' % (key, nargs))

            # type: convert to specified type
            newtype = config.get('type', None)
            if newtype is not None:
                newval = []
                for v in val:
                    try:
                        newval.append(newtype(v))
                    except ValueError:
                        reason = "%s: type error ?%s=%s to %r" % (key, name, v, newtype)
                        raise HTTPError(BAD_REQUEST, reason=reason)
                val = newval

            # choices: check valid items
            choices = config.get('choices', None)
            if isinstance(choices, (list, dict, set)):
                choices = set(choices)
                for v in val:
                    if v not in choices:
                        reason = '%s: invalid choice ?%s=%s' % (key, name, v)
                        raise HTTPError(BAD_REQUEST, reason=reason)

            # Set the final value
            if nargs is None:
                if len(val) > 0:
                    result[key] = val[-1]
            else:
                result[key] = val

        # Parse remaining keys
        if args_type is list:
            for key, val in self.args.items():
                if key not in args and key not in kwargs:
                    result[key] = val
        elif args_type in (six.string_types, six.binary_type):
            for key, val in self.args.items():
                if key not in args and key not in kwargs:
                    result[key] = args_type(val[0])

        return result


class BaseWebSocketHandler(WebSocketHandler, BaseMixin):
    def initialize(self, **kwargs):
        self._session, self._session_json = None, 'null'
        if self.cache:
            self.cachefile = self.cache()
            self.original_get = self.get
            self.get = self._cached_get
        if self._set_xsrf:
            self.xsrf_token

    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        for method in self._on_init_methods:
            method(self)
        super(BaseWebSocketHandler, self).get(*args, **kwargs)

    def on_close(self):
        # Loop through class-level callbacks
        for callback in self._on_finish_methods:
            callback(self)

    def get_current_user(self):
        '''Return the ``user`` key from the session as an AttrDict if it exists.'''
        result = self.session.get('user')
        return AttrDict(result) if isinstance(result, dict) else result

    def authorize(self):
        '''If a valid user isn't logged in, send a message and close connection'''
        if not self.current_user:
            raise HTTPError(UNAUTHORIZED)
        for permit_generator in self.permissions:
            for result in permit_generator(self):
                if not result:
                    raise HTTPError(FORBIDDEN)


class KeyStore(object):
    '''
    Base class for persistent dictionaries. (But KeyStore is not persistent.)

        >>> store = KeyStore(path)
        >>> value = store.load(key, None)   # Load a value. It's like dict.get()
        >>> store.dump(key, value)          # Save a value. It's like dict.set(), but doesn't flush
        >>> store.flush()                   # Saves to disk
        >>> store.close()                   # Close the store

    You can initialize a KeyStore with a ``flush=`` parameter. The store is
    flushed to disk via ``store.flush()`` every ``flush`` seconds.

    If a ``purge=`` function is provided, it is called with with the data. The
    function can change the data in-place, for example, removing any expired
    entries. The return value is ignored.

    When the program exits, ``.close()`` is automatically called.
    '''
    def __init__(self, path, flush=None, purge=None):
        '''Initialise the KeyStore at path'''
        # Ensure that path directory exists
        self.path = os.path.abspath(path)
        folder = os.path.dirname(self.path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.store = {}
        # Periodically flush buffers
        if flush is not None:
            tornado.ioloop.PeriodicCallback(self.flush, callback_time=flush * 1000).start()
        if callable(purge):
            self.purge = purge
        elif purge is None:
            self.purge = lambda data: None
        else:
            app_log.error('KeyStore: purge=%r invalid. Must be callable', purge)
        # Call close() when Python gracefully exits
        atexit.register(self.close)

    def keys(self):
        '''Return all keys in the store'''
        return self.store.keys()

    def load(self, key, default=None):
        '''Same as store.get(), but called "load" to indicate persistence'''
        return self.store.get(key, {} if default is None else default)

    def dump(self, key, value):
        '''Same as store[key] = value'''
        self.store[key] = value

    def flush(self):
        '''Write to disk'''
        self.purge(self.store)

    def close(self):
        '''Flush and close all open handles'''
        raise NotImplementedError()


class HDF5Store(KeyStore):
    '''
    A KeyStore that stores data in a HDF5 file. Typical usage::

        >>> store = HDF5Store('file.h5', flush=15)
        >>> value = store.load(key)
        >>> store.dump(key, value)

    Internally, it uses HDF5 groups to store data. Values are encoded as JSON
    using gramex.config.CustomJSONEncoder (thus handling datetime.) Keys are JSON
    encoded, and '/' is escaped as well (since HDF5 groups treat / as subgroups.)
    '''
    def __init__(self, path, *args, **kwargs):
        super(HDF5Store, self).__init__(path, *args, **kwargs)
        import h5py
        self.store = h5py.File(self.path, 'a')
        self.changed = False

    def load(self, key, default=None):
        # Keys cannot contain / in HDF5 store. Escape it
        key = json.dumps(key, ensure_ascii=True)[1:-1].replace('/', '\t')
        result = self.store.get(key, None)
        if result is None:
            return default
        try:
            return json.loads(result.value, object_pairs_hook=AttrDict, cls=CustomJSONDecoder)
        except ValueError:
            app_log.error('HDF5Store("%s").load("%s") is not JSON ("%r..."")',
                          self.path, key, result.value)
            return default

    def dump(self, key, value):
        # Keys cannot contain / in HDF5 store. Escape it
        key = json.dumps(key, ensure_ascii=True)[1:-1].replace('/', '\t')
        if self.store.get(key) != value:
            if key in self.store:
                del self.store[key]
            self.store[key] = json.dumps(value, ensure_ascii=True, separators=(',', ':'),
                                         cls=CustomJSONEncoder)
            self.changed = True

    def keys(self):
        # Keys cannot contain / in HDF5 store. Unescape it
        return [json.loads('"%s"' % key.replace('\t', '/')) for key in self.store.keys()]

    def flush(self):
        super(HDF5Store, self).flush()
        if self.changed:
            app_log.debug('Flushing %s', self.path)
            self.store.flush()
            self.changed = False

    def close(self):
        try:
            self.store.close()
        # h5py.h5f.get_obj_ids often raises a ValueError: Not a file id.
        # This is presumably if the file handle has been closed. Log & ignore.
        except ValueError:
            app_log.debug('HDF5Store("%s").close() error ignored', self.path)


class JSONStore(KeyStore):
    '''
    A KeyStore that stores data in a JSON file. Typical usage::

        >>> store = JSONStore('file.json', flush=15)
        >>> value = store.load(key)
        >>> store.dump(key, value)

    This is less efficient than HDF5Store for large data, but is human-readable.
    They also cannot support multiple instances. Only one JSONStore instance
    is permitted per file.
    '''
    def __init__(self, path, *args, **kwargs):
        super(JSONStore, self).__init__(path, *args, **kwargs)
        try:
            self.handle = open(self.path, 'r+')     # noqa: no encoding for json
            self.store = json.load(self.handle, cls=CustomJSONDecoder)
        except (IOError, ValueError):
            self.handle = open(self.path, 'w')      # noqa: no encoding for json
            self.store = {}
        self.changed = False

    def dump(self, key, value):
        '''Same as store[key] = value'''
        if self.store.get(key) != value:
            self.store[key] = value
            self.changed = True

    def flush(self):
        super(JSONStore, self).flush()
        if self.changed:
            app_log.debug('Flushing %s', self.path)
            json_value = json.dumps(self.store, ensure_ascii=True, separators=(',', ':'),
                                    cls=CustomJSONEncoder)
            self.handle.seek(0)
            self.handle.write(json_value)
            self.handle.flush()
            self.changed = False

    def close(self):
        self.flush()
        self.handle.close()


def check_membership(memberships):
    '''
    Return a generator that checks all memberships for a user, and yields True if
    any membership is allowed, else False
    '''
    # Pre-process memberships into an array of {objectpath: set(values)}
    conds = [{
        keypath: set(values) if isinstance(values, list) else {values}
        for keypath, values in cond.items()
    } for cond in memberships]

    def allowed(self):
        user = self.current_user
        for cond in conds:
            if _check_condition(cond, user):
                yield True
                break
        else:
            yield False

    return allowed


def _check_condition(condition, user):
    '''
    A condition is a dictionary of {keypath: values}. Extract the keypath from
    the user. Check if the value is in the values list. If not, this condition
    fails.
    '''
    for keypath, values in condition.items():
        node = objectpath(user, keypath)
        # If nothing exists at keypath, the check fails
        if node is None:
            return False
        # If the value is a list, it must overlap with values
        elif isinstance(node, list):
            if not set(node) & values:
                return False
        # If the value is not a list, it must be present in values
        elif node not in values:
            return False
    return True


handle_cache = {}


def _handle(path):
    '''Returns a cached append-binary handle to path'''
    if path not in handle_cache:
        # In Python 2, csv writerow writes byte string. In PY3, it's to a unicode string.
        # Open file handles accordingly
        handle_cache[path] = open(path, 'ab') if six.PY2 else io.open(path, 'a', encoding='utf-8')
    return handle_cache[path]


def log_method(log):
    '''
    Returns a log_request method that can be called as log_request(handler).
    The method logs handler request information.

    ``log`` is a dict that determines how request logs are saved. For example::

        format: csv
        path: $GRAMEXDATA/logs/request.csv
        keys: [time, method, uri, ip, status, duration, user, ...]

    This saves the logs at path as a CSV file with the columns being the keys specified

    An alternate format is::

        format: '%(status)d %(method)s %(uri)s (%(ip)s) %(duration).1fms %(user.id)s'

    This writes the result to the logger (defaults to tornado.log.access_log).
    '''
    if log is None:
        return
    if not isinstance(log, dict) or 'format' not in log:
        raise ValueError('log: is not a dict with a format key')
    # Define direct keys. These can be used as-is
    direct_vars = {
        'time': 'round(time.time() * 1000, 0)',
        'method': 'handler.request.method',
        'uri': 'handler.request.uri',
        'ip': 'handler.request.remote_ip',
        'status': 'handler.get_status()',
        'duration': 'round(handler.request.request_time() * 1000, 0)',
        # TODO: get_content_size() is not available in RequestHandler
        # 'size': 'handler.get_content_size()',
        'user': 'json.dumps(handler.current_user)',
        'session': 'handler.session.get("id", "")',
        'error': 'getattr(handler, "_exception", "")',
    }
    # Define object keys for us as key.value. E.g. cookies.sid, user.email, etc
    object_vars = {
        'args': 'handler.get_argument("{val}", "")',
        'request': 'getattr(handler.request, "{val}", "")',
        'headers': 'handler.request.headers.get("{val}", "")',
        'cookies': 'handler.request.cookies["{val}"].value ' +
                   'if "{val}" in handler.request.cookies else ""',
        'user': '(handler.current_user or {{}}).get("{val}", "")',
        'env': 'os.environ.get("{val}", "")',
    }
    context = {'os': os, 'time': time, 'json': json}
    # Generate the code
    if log.get('format') == 'csv':
        try:
            keys = log['keys']
        except KeyError:
            raise ValueError('log.keys missing')
        if 'path' not in log:
            raise ValueError('log.path missing')
        log_path = os.path.abspath(log['path'])
        path_dir = os.path.dirname(log_path)
        try:
            if not os.path.exists(path_dir):
                os.makedirs(path_dir)
            handle = _handle(log_path)
            writer = csv.writer(handle)
        except OSError:
            raise OSError('Cannot open log.path: %s as CSV' % log_path)
        assign = '        {value},'
        code = dedent('''
            def log_request(handler, writer=writer, handle=handle):
                writer.writerow([
            %s
                ])
                handle.flush()
        ''')
        context.update(writer=writer, handle=handle)
    else:
        keys = DefaultAttrDict(int)
        try:
            log['format'] % keys
        except (TypeError, ValueError):
            raise ValueError('log.format invalid: %s' % log['format'])
        assign = '    obj["{key}"] = {value}'
        code = dedent('''
            def log_request(handler, logger=logger):
                obj = {}
                status = obj['status'] = handler.get_status()
            %s
                if status < 400:
                    logger.info(log_format %% obj)
                elif status < 500:
                    logger.warning(log_format %% obj)
                else:
                    logger.error(log_format %% obj)
        ''')
        context.update(log_format=log['format'], logger=access_log)
    obj = []
    for key in keys:
        if key in direct_vars:
            obj.append(assign.format(key=key, value=direct_vars[key]))
            continue
        if '.' in key:
            prefix, value = key.split('.', 2)
            if prefix in object_vars:
                obj.append(assign.format(key=key, value=object_vars[prefix].format(val=value)))
                continue
        app_log.error('Skipping unknown key %s in log.format: %s', key, log['format'])
    code = compile(code % '\n'.join(obj), filename='log_method', mode='exec')
    exec(code, context)
    return context['log_request']
