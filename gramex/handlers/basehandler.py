from __future__ import unicode_literals

import io
import os
import six
import json
import time
import atexit
import logging
import datetime
import mimetypes
import traceback
import tornado.gen
import gramex.cache
from binascii import b2a_base64, hexlify
from orderedattrdict import AttrDict
from six.moves.urllib_parse import urlparse, urlsplit, urljoin, urlencode
from tornado.web import RequestHandler, HTTPError, MissingArgumentError
from tornado.websocket import WebSocketHandler
from gramex import conf, __version__
from gramex.services import info
from gramex.config import merge, objectpath, app_log, CustomJSONDecoder, CustomJSONEncoder
from gramex.transforms import build_transform
from gramex.http import UNAUTHORIZED, FORBIDDEN, BAD_REQUEST

server_header = 'Gramex/%s' % __version__
session_store_cache = {}
_missing = object()


class BaseMixin(object):
    @classmethod
    def setup(cls, transform={}, redirect={}, auth=None, log=None, set_xsrf=None,
              error=None, xsrf_cookies=None, **kwargs):
        '''
        One-time setup for all request handlers. This is called only when
        gramex.yaml is parsed / changed.
        '''
        cls._on_init_methods = []
        cls._on_finish_methods = []
        cls._set_xsrf = set_xsrf

        cls.kwargs = cls.conf.get('kwargs', AttrDict())
        cls.setup_default_kwargs()

        cls.setup_transform(transform)
        cls.setup_redirect(redirect)
        # Note: call setup_session before setup_auth to ensure that
        # override_user is run before authorize
        cls.setup_session(conf.app.get('session'))
        cls.setup_auth(auth)
        # Update defaults from BaseHandler. Only error (for now).
        # Use objectpath instead of a direct reference - in case handler.BaseHandler is undefined
        cls.setup_log()
        cls.setup_error(error or objectpath(conf, 'handlers.BaseHandler.error', {}))
        cls.setup_xsrf(xsrf_cookies)

        # app.settings.debug enables debugging exceptions using pdb
        if conf.app.settings.get('debug', False):
            cls.log_exception = cls.debug_exception

    @classmethod
    def clear_special_keys(cls, kwargs, *args):
        '''
        Remove keys handled by BaseHandler that may interfere with setup().
        This should be called explicitly in setup() where required.
        '''
        # TODO: make this more robust / cleaner
        for special_key in ['transform', 'redirect', 'auth', 'log', 'set_xsrf',
                            'error', 'xsrf_cookies', 'headers']:
            kwargs.pop(special_key, None)
        for special_key in args:
            kwargs.pop(special_key, None)

    @classmethod
    def setup_default_kwargs(cls):
        '''Use configs under handlers.<ClassName>.* as the default for kwargs'''
        update = objectpath(conf, 'handlers.' + cls.conf.handler, {})
        merge(cls.conf.setdefault('kwargs', {}), update, mode='setdefault')

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
    def _purge_keys(data):
        '''
        Returns keys to be deleted. These are either None values or
        those with expired keys based on _t.
        setup_session makes the session store call this method.
        Until v1.20 (31 Jul 2017) no _t keys were set.
        From v1.23 (31 Oct 2017) these are cleared.
        '''
        now = time.time()
        week = 7 * 24 * 60 * 60
        keys = []
        # When using sqlitedict, fetching keys may fail if DB is locked. Try later
        try:
            items = list(data.items())
        except Exception:
            items = []
        for key, val in items:
            # Purge already cleared / removed sessions
            if val is None:
                keys.append(key)
            elif isinstance(val, dict):
                # If the session has expired, remove it
                if val.get('_t', 0) < now:
                    keys.append(key)
                # If the session is inactive, remove it after a week.
                # If we remove immediately, then we may lose WIP sessions.
                # For example, people who opened a login page where _next_url was set
                elif '_i' in val and '_l' in val and val['_i'] + val['_l'] < now - week:
                    keys.append(key)
        return keys

    @classmethod
    def setup_session(cls, session_conf):
        '''handler.session returns the session object. It is saved on finish.'''
        if session_conf is None:
            return
        key = store_type, store_path = session_conf.get('type'), session_conf.get('path')
        kwargs = dict(
            path=store_path,
            flush=session_conf.get('flush'),
            purge=session_conf.get('purge'),
            purge_keys=cls._purge_keys
        )
        if key in session_store_cache:
            pass
        elif store_type == 'memory':
            session_store_cache[key] = KeyStore(**kwargs)
        elif store_type == 'sqlite':
            session_store_cache[key] = SQLiteStore(**kwargs)
        elif store_type == 'json':
            session_store_cache[key] = JSONStore(**kwargs)
        elif store_type == 'hdf5':
            session_store_cache[key] = HDF5Store(**kwargs)
        else:
            raise NotImplementedError('Session type: %s not implemented' % store_type)
        cls._session_store = session_store_cache[key]
        cls.session = property(cls.get_session)
        cls._session_expiry = session_conf.get('expiry')
        cls._on_finish_methods.append(cls.save_session)
        cls._on_init_methods.append(cls.override_user)
        cls._on_finish_methods.append(cls.set_last_visited)

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
            cls._login_url = auth.get('login_url', None)
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
    def setup_log(cls):
        '''
        Logs access requests to gramex.requests as a CSV file.
        '''
        logger = logging.getLogger('gramex.requests')
        keys = objectpath(conf, 'log.handlers.requests.keys', [])
        log_info = build_log_info(keys)
        cls.log_request = lambda handler: logger.info(log_info(handler))

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
                if error_code < 100 or error_code > 1000:
                    raise ValueError()
            except ValueError:
                app_log.error('url.%s.error code %s is not a number (100 - 1000)',
                              cls.name, error_code)
                continue
            if not isinstance(error_config, dict):
                return app_log.error('url:%s.error.%d is not a dict', cls.name, error_code)
            # Make a copy of the original. When we add headers, etc, it shouldn't affect original
            error_config = AttrDict(error_config)
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

                def get_error_fn(error_config):
                    def error(*args, **kwargs):
                        tmpl = gramex.cache.open(error_config['path'], 'template', autoescape=None)
                        return tmpl.generate(*args, **kwargs)
                    return error

                cls.error[error_code] = {'function': get_error_fn(error_config)}
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
        cls.check_xsrf_cookie = cls.noop if xsrf_cookies is False else cls.xsrf_ajax

    def xsrf_ajax(self):
        '''
        TODO: explain things clearly.
        Same as Tornado's check_xsrf_cookie() -- but is ignored for AJAX requests
        '''
        ajax = self.request.headers.get('X-Requested-With', '').lower() == 'xmlhttprequest'
        if not ajax:
            return super(BaseHandler, self).check_xsrf_cookie()

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
        set it up first. Then redirect.

        See :py:func:`setup_redirect`
        '''
        if '_next_url' not in self.session:
            self.save_redirect_page()
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
        import ipdb as pdb              # noqa
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
        Return the session object for the cookie "sid" value.
        If no "sid" cookie exists, set up a new one.
        If no session object exists for the sid, create it.
        By default, the session object contains a "id" holding the "sid" value.

        The session is a dict. You must ensure that it is JSON serializable.

        Sessions use these pre-defined timing keys (values are timestamps):

        - ``_t`` is the expiry time of the session
        - ``_l`` is the last time the user accessed a page. Updated by
          :py:func:`BaseHandler.set_last_visited`
        - ``_i`` is the inactive expiry duration in seconds, i.e. if ``now > _l +
          _i``, the session has expired.

        ``new=`` creates a new session to avoid session fixation.
        https://www.owasp.org/index.php/Session_fixation.
        :py:func:`gramex.handlers.authhandler.AuthHandler.set_user` uses it.
        When the user logs in:

        - If no old session exists, it returns a new session object.
        - If an old session exists, it creates a new "sid" and new session
          object, copying all old contents, but updates the "id" and expiry (_t).
        '''
        if expires_days is None:
            expires_days = self._session_expiry
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
        s = self._session
        old_sid = s['id']
        # If session has expiry keys _i and _l defined, check for expiry. Not otherwise
        if '_i' in s and '_l' in s and time.time() > s['_l'] + s['_i']:
            new = True
            s.clear()
        if new and not created_new_sid:
            new_sid = self._set_new_session_id(expires_days).decode('ascii')
            # Update expiry and new SID on session
            s.update(id=new_sid, _t=time.time() + expires_days * 24 * 60 * 60)
            # Delete old contents. No _t also means expired
            self._session_store.dump(old_sid, {})

        return s

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
                user = info['encrypt'].decrypt(cipher)
            except Exception:
                reason = '%s: invalid X-Gramex-User: %s' % (self.name, cipher)
                raise HTTPError(BAD_REQUEST, reason=reason)
            else:
                app_log.debug('%s: Overriding user to %r', self.name, user)
                self.session['user'] = user
                return
        otp = headers.get('X-Gramex-OTP') or self.get_argument('gramex-otp', None)
        if otp:
            otp_data = self._session_store.load('otp:' + otp, None)
            if not isinstance(otp_data, dict) or '_t' not in otp_data or 'user' not in otp_data:
                reason = '%s: invalid X-Gramex-OTP: %s' % (self.name, otp)
                raise HTTPError(BAD_REQUEST, reason=reason)
            elif otp_data['_t'] < time.time():
                reason = '%s: expired X-Gramex-OTP: %s' % (self.name, otp)
                raise HTTPError(BAD_REQUEST, reason=reason)
            self._session_store.dump('otp:' + otp, None)
            self.session['user'] = otp_data['user']

    def set_last_visited(self):
        '''
        This method is called by :py:func:`BaseHandler.prepare` when any user
        accesses a page. It updates the last visited time in the ``_l`` session
        key. It does this only if the ``_i`` key exists.
        '''
        # For efficiency reasons, don't call get_session every time. Check
        # session only if there's a valid sid cookie (with possibly long expiry)
        if self.get_secure_cookie('sid', max_age_days=9999999):
            session = self.get_session()
            if '_i' in session:
                session['_l'] = time.time()


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
            self.request.method = self.args.pop('x-http-method-override')[0].upper()
        elif 'X-HTTP-Method-Override' in self.request.headers:
            self.request.method = self.request.headers['X-HTTP-Method-Override'].upper()

    def get_arg(self, name, default=RequestHandler._ARG_DEFAULT, first=False):
        '''
        Returns the value of the argument with the given name. Similar to
        ``.get_argument`` but uses ``self.args`` instead.

        If default is not provided, the argument is considered to be
        required, and we raise a `MissingArgumentError` if it is missing.

        If the argument is repeated, we return the last value. If ``first=True``
        is passed, we return the first value.

        ``self.args`` is always UTF-8 decoded unicode. Whitespaces are stripped.
        '''
        if name not in self.args:
            if default is RequestHandler._ARG_DEFAULT:
                raise MissingArgumentError(name)
            return default
        return self.args[name][0 if first else -1]

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
        if not self.current_user:
            # Redirect non-AJAX requests GET/HEAD to login URL (if it's a string)
            ajax = self.request.headers.get('X-Requested-With', '').lower() == 'xmlhttprequest'
            if self.request.method in ('GET', 'HEAD') and not ajax:
                url = self.get_login_url() if self._login_url is None else self._login_url
                # If login_url is a string, redirect
                if isinstance(url, six.string_types):
                    if '?' not in url:
                        if urlsplit(url).scheme:
                            # if login url is absolute, make next absolute too
                            next_url = self.request.full_url()
                        else:
                            next_url = self.request.uri
                        url += '?' + urlencode(dict(next=next_url))
                    self.redirect(url)
                    return
            # Else, send a 401 header
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

    If a ``purge=`` is provided, the data is purged of missing values every
    ``purge`` seconds. You can provide a custom ``purge_keys=`` function that
    returns an iterator of keys to delete if any.

    When the program exits, ``.close()`` is automatically called.
    '''
    def __init__(self, path, flush=None, purge=None, purge_keys=None):
        '''Initialise the KeyStore at path'''
        # Ensure that path directory exists
        self.path = os.path.abspath(path)
        folder = os.path.dirname(self.path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.store = {}
        if callable(purge_keys):
            self.purge_keys = purge_keys
        elif purge_keys is not None:
            app_log.error('KeyStore: purge_keys=%r invalid. Must be function(dict)', purge_keys)
        # Periodically flush and purge buffers
        if flush is not None:
            tornado.ioloop.PeriodicCallback(self.flush, callback_time=flush * 1000).start()
        if purge is not None:
            tornado.ioloop.PeriodicCallback(self.purge, callback_time=purge * 1000).start()
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

    @staticmethod
    def purge_keys(data):
        return [key for key, val in data.items() if val is None]

    def flush(self):
        '''Write to disk'''
        pass

    def purge(self):
        '''Delete empty keys and flush'''
        for key in self.purge_keys(self.store):
            try:
                del self.store[key]
            except KeyError:
                # If the key was already removed from store, ignore
                pass
        self.flush()

    def close(self):
        '''Flush and close all open handles'''
        raise NotImplementedError()


class SQLiteStore(KeyStore):
    '''
    A KeyStore that stores data in a SQLite file. Typical usage::

        >>> store = SQLiteStore('file.db')
        >>> value = store.load(key)
        >>> store.dump(key, value)

    Values are encoded as JSON using gramex.config.CustomJSONEncoder (thus
    handling datetime.) Keys are JSON encoded.
    '''
    def __init__(self, path, table='store', *args, **kwargs):
        super(SQLiteStore, self).__init__(path, *args, **kwargs)
        from sqlitedict import SqliteDict
        self.store = SqliteDict(
            self.path, tablename=table, autocommit=True,
            encode=lambda v: json.dumps(v, separators=(',', ':'), ensure_ascii=True,
                                        cls=CustomJSONEncoder),
            decode=lambda v: json.loads(v, object_pairs_hook=AttrDict, cls=CustomJSONDecoder),
        )

    def close(self):
        self.store.close()

    def flush(self):
        super(SQLiteStore, self).flush()
        self.store.commit()

    def purge(self):
        app_log.debug('Purging %s', self.path)
        super(SQLiteStore, self).purge()


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
        self.changed = False
        import h5py
        # h5py.File fails with OSError: Unable to create file (unable to open file: name =
        # '.meta.h5', errno = 17, error message = 'File exists', flags = 15, o_flags = 502)
        # TODO: identify why this happens and resolve it.
        self.store = h5py.File(self.path, 'a')

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

    def purge(self):
        '''
        Load all keys into self.store. Delete what's required. Save.
        '''
        self.flush()
        changed = False
        items = {key: json.loads(val.value, object_pairs_hook=AttrDict, cls=CustomJSONDecoder)
                 for key, val in self.store.items()}
        for key in self.purge_keys(items):
            del self.store[key]
            changed = True
        if changed:
            app_log.debug('Purging %s', self.path)
            self.store.flush()

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
        self.store = self._read_json()
        self.changed = False
        self.update = {}        # key-values added since flush

    def _read_json(self):
        try:
            with open(self.path) as handle:         # noqa: no encoding for json
                return json.load(handle, cls=CustomJSONDecoder)
        except (IOError, ValueError):
            return {}

    def _write_json(self, data):
        json_value = json.dumps(data, ensure_ascii=True, separators=(',', ':'),
                                cls=CustomJSONEncoder)
        with open(self.path, 'w') as handle:    # noqa: no encoding for json
            handle.write(json_value)

    def dump(self, key, value):
        '''Same as store[key] = value'''
        if self.store.get(key) != value:
            self.store[key] = value
            self.update[key] = value
            self.changed = True

    def flush(self):
        super(JSONStore, self).flush()
        if self.changed:
            app_log.debug('Flushing %s', self.path)
            store = self._read_json()
            store.update(self.update)
            self._write_json(store)
            self.store = store
            self.update = {}
            self.changed = False

    def purge(self):
        '''
        Load all keys into self.store. Delete what's required. Save.
        '''
        self.flush()
        changed = False
        for key in self.purge_keys(self.store):
            del self.store[key]
            changed = True
        if changed:
            app_log.debug('Purging %s', self.path)
            self._write_json(self.store)

    def close(self):
        try:
            self.flush()
        # This has happened when the directory was deleted. Log & ignore.
        except OSError:
            app_log.error('Cannot flush %s', self.path)


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


def build_log_info(keys, *vars):
    '''
    Creates a ``handler.method(vars)`` that returns a dictionary of computed
    values. ``keys`` defines what keys are returned in the dictionary. The values
    are computed using the formulas in the code.
    '''
    # Define direct keys. These can be used as-is
    direct_vars = {
        'name': 'handler.name',
        'class': 'handler.__class__.__name__',
        'time': 'round(time.time() * 1000, 0)',
        'datetime': 'datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")',
        'method': 'handler.request.method',
        'uri': 'handler.request.uri',
        'ip': 'handler.request.remote_ip',
        'status': 'handler.get_status()',
        'duration': 'round(handler.request.request_time() * 1000, 0)',
        'port': 'conf.app.listen.port',
        # TODO: get_content_size() is not available in RequestHandler
        # 'size': 'handler.get_content_size()',
        'user': '(handler.current_user or {}).get("id", "")',
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
    vals = []
    for key in keys:
        if key in vars:
            vals.append('"{}": {},'.format(key, key))
            continue
        if key in direct_vars:
            vals.append('"{}": {},'.format(key, direct_vars[key]))
            continue
        if '.' in key:
            prefix, value = key.split('.', 2)
            if prefix in object_vars:
                vals.append('"{}": {},'.format(key, object_vars[prefix].format(val=value)))
                continue
        app_log.error('Skipping unknown key %s', key)
    code = compile('def fn(handler, %s):\n\treturn {%s}' % (', '.join(vars), ' '.join(vals)),
                   filename='log', mode='exec')
    context = {'os': os, 'time': time, 'datetime': datetime, 'conf': conf, 'AttrDict': AttrDict}
    # The code is constructed entirely by this function. Using exec is safe
    exec(code, context)         # nosec
    return context['fn']
