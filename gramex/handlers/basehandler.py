import io
import os
import six
import time
import logging
import mimetypes
import traceback
import tornado.gen
import gramex.cache
from typing import Union
from binascii import b2a_base64, hexlify
from fnmatch import fnmatch
from http.cookies import Morsel
from orderedattrdict import AttrDict
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urljoin, urlencode
from tornado.web import RequestHandler, HTTPError, MissingArgumentError, decode_signed_value
from tornado.websocket import WebSocketHandler
from gramex import conf, __version__
from gramex.config import merge, objectpath, app_log
from gramex.transforms import build_transform, build_log_info, CacheLoader
from gramex.http import UNAUTHORIZED, FORBIDDEN, BAD_REQUEST, METHOD_NOT_ALLOWED
from gramex.cache import get_store
# We don't use these, but these stores used to be defined here. Programs may import these
from gramex.cache import KeyStore, JSONStore, HDF5Store, SQLiteStore, RedisStore    # noqa

server_header = f'Gramex/{__version__}'
session_store_cache = {}

# Python 3.8+ supports SameSite cookie attribute. Monkey-patch it for Python 3.7
# https://stackoverflow.com/a/50813092/100904
Morsel._reserved.setdefault('samesite', 'SameSite')


class BaseMixin(object):
    @classmethod
    def setup(cls, transform={}, redirect={}, methods=None,
              auth: Union[None, bool, dict] = None,
              log=None, set_xsrf=None, error=None, xsrf_cookies=None,
              cors: Union[None, bool, dict] = None,
              **kwargs):
        '''
        One-time setup for all request handlers. This is called only when
        gramex.yaml is parsed / changed.
        '''
        cls._on_init_methods = []
        cls._on_finish_methods = []
        cls._set_xsrf = set_xsrf

        cls.kwargs = cls.conf.get('kwargs', AttrDict())

        cls.setup_transform(transform)
        cls.setup_redirect(redirect)
        # Note: call setup_session before setup_auth to ensure that
        # override_user is run before authorize
        cls.setup_session(conf.app.get('session'))
        cls.setup_auth(auth)
        cls.setup_error(error)
        cls.setup_xsrf(xsrf_cookies)
        cls.setup_log()
        cls.setup_httpmethods(methods)
        cls.setup_cors(cors, auth=auth)

        # app.settings.debug enables debugging exceptions using pdb
        if conf.app.settings.get('debug', False):
            cls.log_exception = cls.debug_exception

    # A list of special keys for BaseHandler. Can be extended by other classes.
    special_keys = ['transform', 'redirect', 'methods', 'auth', 'log', 'set_xsrf',
                    'error', 'xsrf_cookies', 'cors', 'headers']

    @classmethod
    def clear_special_keys(cls, kwargs, *args):
        '''
        Remove keys handled by BaseHandler that may interfere with setup().
        This should be called explicitly in setup() where required.
        '''
        for special_key in cls.special_keys:
            kwargs.pop(special_key, None)
        for special_key in args:
            kwargs.pop(special_key, None)
        return kwargs

    @classmethod
    def get_list(cls, val: Union[list, tuple, str], key: str = '', eg: str = '', caps=True) -> set:
        '''
        Convert val="GET, PUT" into {"GET", "PUT"}.
        If val is not a string or list/tuple, raise ValueError("url.{key} invalid. e.g. {eg}")
        '''
        if isinstance(val, (list, tuple)):
            val = ' '.join(val)
        elif not val:
            val = ''
        if not isinstance(val, str):
            err = f'url:{cls.name}.{key}: {val!r} not a string/list'
            err = err + f', e.g. {eg}' if eg else err
            raise ValueError(err)
        if caps:
            val = val.upper()
        return set(val.replace(',', ' ').split())

    @classmethod
    def setup_httpmethods(cls, methods: Union[list, tuple, str]):
        methods = cls.get_list(methods, key='methods', eg='[GET, POST]', caps=True)
        if methods:
            cls._http_methods = methods
            cls._on_init_methods.append(cls.check_http_method)

    def check_http_method(self):
        '''If method: [...] is specified, reject all methods not in the allowed methods set'''
        if self.request.method not in self._http_methods:
            raise HTTPError(METHOD_NOT_ALLOWED, f'{self.name}: method {self.request.method} ' +
                            f'not in allowed methods {self._http_methods}')

    @classmethod
    def setup_cors(cls, cors: Union[None, bool, dict], auth):
        if cors is None:
            return
        if cors is True:
            cors = {
                'auth': bool(auth),
                'methods': '*',
                'headers': '*',
                'origins': '*',
            }
        if not isinstance(cors, dict):
            app_log.error(f'url:{cls.name}.cors is not a dict/True')
            return
        cls._cors = cors
        # Set default CORS values as a set
        for key in ('origins', 'methods', 'headers'):
            cors[key] = cls.get_list(cors.get(key, '*'), f'cors.{key}', '"*"', caps=False)
        cls._on_init_methods.append(cls.check_cors)
        cls.options = cls._cors_options

    def check_cors(self):
        '''
        For simple CORS requests, send Access-Control-Allow-Origin: <origin>.
        If request needs credentials, allow it.'''
        origin, cred = self.cors_origin()
        if origin:
            self.set_header('Access-Control-Allow-Origin', origin)
            if cred:
                self.set_header('Access-Control-Allow-Credentials', 'true')

    def cors_origin(self):
        '''
        Returns the origin to set in Access-Control-Allow-Origin header.
        '''
        # If CORS is not enabled, it fails
        if not self._cors:
            return None, False
        # Assume credentials are passed if handler requires Auth or Cookie is passed
        cred = self._cors['auth'] or self.request.headers.get('Cookie')
        # If origin: *, then allow all origins
        origin = self.request.headers.get('Origin', '').lower()
        if self._cors['origins'] == set('*'):
            return (origin if cred else '*', cred)
        # If it matches any of the wildcards, return specific origin
        for pattern in self._cors['origins']:
            if fnmatch(origin, pattern.lower()):
                return origin, cred
        # If none of the patterns match, it fails
        return None, cred

    def _cors_options(self, *args, **kwargs):
        # Check if origin is in cors.origin
        origin, cred = self.cors_origin()
        if not origin:
            origin = self.request.headers.get('Origin', '')
            raise HTTPError(BAD_REQUEST, f'url:{self.name}: CORS origin {origin} '
                                         f'not in {self._cors["origins"]}')

        # Check if method is in cors.methods
        method = self.request.headers.get('Access-Control-Request-Method', '').upper()
        for pattern in self._cors['methods']:
            if fnmatch(method, pattern.upper()):
                break
        else:
            raise HTTPError(BAD_REQUEST, f'url:{self.name}: CORS method {method} '
                                         f'not in {self._cors["methods"]}')

        # Check if headers is in cors.headers
        headers = self.request.headers.get('Access-Control-Request-Headers', '')
        headers = self.get_list(headers, 'headers', '', caps=False)
        allowed_headers = set([h.lower() for h in self._cors['headers']])
        diff = set()
        if '*' not in allowed_headers:
            for header in headers:
                if header.lower() not in allowed_headers:
                    diff.add(header)
        if diff:
            raise HTTPError(BAD_REQUEST, f'url:{self.name}: CORS headers {diff} '
                                         f'not in {self._cors["headers"]}')

        # If it succeeds, set relevant headers
        self.set_header('Access-Control-Allow-Origin', origin)
        methods = (self._all_methods if '*' in self._cors['methods']
                   else ', '.join(self._cors['methods']))
        self.set_header('Access-Control-Allow-Methods', methods)
        headers |= self._cors['headers']
        if '*' in headers:
            headers.remove('*')
            headers.update(self._all_headers)
        self.set_header('Access-Control-Allow-Headers', ', '.join(headers))
        # TODO: Access-Control-Max-Age
        # TODO: Access-Control-Expose-Headers

    _all_methods = 'GET, HEAD, POST, PUT, DELETE, OPTIONS, PATCH, CONNECT, TRACE'
    _all_headers = [
        'Accept',
        'Cache-Control',
        'Content-Type',
        'If-None-Match',
        'Origin',
        'Pragma',
        'Upgrade-Insecure-Requests',
        'X-Requested-With',
    ]

    @classmethod
    def setup_default_kwargs(cls):
        '''
        Use default config from handlers.<Class>.* and handlers.BaseHandler.
        Called directly by gramex.services.url().
        NOTE: This updates the kwargs for setup() -- so it must be called BEFORE setup()
        and can't be merged into setup() or called from setup().
        '''
        c = cls.conf.kwargs
        merge(c, objectpath(conf, 'handlers.' + cls.conf.handler, {}), mode='setdefault')
        merge(c, objectpath(conf, 'handlers.BaseHandler', {}), mode='setdefault')

    @classmethod
    def setup_transform(cls, transform):
        cls.transform = {}
        for pattern, trans in transform.items():
            cls.transform[pattern] = {
                'function': build_transform(
                    trans, vars=AttrDict((('content', None), ('handler', None))),
                    filename=f'url:{cls.name}'),
                'headers': trans.get('headers', {}),
                'encoding': trans.get('encoding'),
            }

    @staticmethod
    def _purge_keys(data):
        '''
        Returns session keys to be deleted. These are either None values or
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
            else:
                app_log.warning(f'Store key: {key} has value type {type(val)} (not dict)')
        return keys

    @classmethod
    def setup_session(cls, session_conf):
        '''handler.session returns the session object. It is saved on finish.'''
        if session_conf is None:
            return
        key = store_type, store_path = session_conf.get('type'), session_conf.get('path')
        if key not in session_store_cache:
            session_store_cache[key] = get_store(
                type=store_type,
                path=store_path,
                flush=session_conf.get('flush'),
                purge=session_conf.get('purge'),
                purge_keys=cls._purge_keys
            )
        cls._session_store = session_store_cache[key]
        cls.session = property(cls.get_session)
        cls._session_expiry = session_conf.get('expiry')
        cls._session_cookie_id = session_conf.get('cookie', 'sid')
        cls._session_cookie = {
            # Note: We cannot use path: to specify the Cookie path attribute.
            # session.path is used for the session (JSONStore) file location.
            key: session_conf[key] for key in ('httponly', 'secure', 'samesite', 'domain')
            if key in session_conf
        }
        cls._on_init_methods.append(cls.override_user)
        cls._on_finish_methods.append(cls.set_last_visited)
        # Ensure that session is saved AFTER we set last visited
        cls._on_finish_methods.append(cls.save_session)

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
        if isinstance(redirect, str):
            redirect = {'url': redirect}
        if not isinstance(redirect, dict):
            app_log.error(f'url:{cls.name}.redirect must be a URL or a dict, not {redirect!r}')
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
                        target = urlsplit(next_uri)
                        if not target.scheme and not target.netloc:
                            return next_uri
                        req = handler.request
                        if req.protocol == target.scheme and req.host == target.netloc:
                            return next_uri
                        app_log.error(f'Not redirecting to external url: {next_uri}')
                return redirect_method
            cls.redirects = [no_external(method) for method in cls.redirects]

    @classmethod
    def setup_auth(cls, auth: Union[None, bool, dict]):
        # auth: if there's no auth: in handler, default to app.auth
        if auth is None:
            auth = conf.app.get('auth')
        # Treat True as an empty dict, i.e. auth: {}
        if auth is True:
            auth = AttrDict()
        # Set up the auth
        if isinstance(auth, dict):
            cls._auth = auth
            cls._auth_methods = cls.get_list(auth.get('methods', ''), 'auth.methods',
                                             '[GET, POST, OPTIONS]')
            cls._on_init_methods.append(cls.authorize)
            cls.permissions = []
            # Add check for condition
            if auth.get('condition'):
                cls.permissions.append(
                    build_transform(auth['condition'], vars=AttrDict(handler=None),
                                    filename=f'url:{cls.name}.auth.permission'))
            # Add check for membership
            memberships = auth.get('membership', [])
            if not isinstance(memberships, list):
                memberships = [memberships]
            if len(memberships):
                cls.permissions.append(check_membership(memberships))
        elif auth:
            app_log.error(f'url:{cls.name}.auth is not a dict')

    def authorize(self):
        '''BaseMixin assumes every handler has an authorize() function'''
        pass

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
    def _error_fn(cls, error_code, error_config):
        template_kwargs = {}
        if 'autoescape' in error_config:
            if not error_config['autoescape']:
                template_kwargs['autoescape'] = None
            else:
                app_log.error(f'url:{cls.name}.error.{error_code}.autoescape can only be false')
        if 'whitespace' in error_config:
            template_kwargs['whitespace'] = error_config['whitespace']

        def error(*args, **kwargs):
            tmpl = gramex.cache.open(error_config['path'], 'template', **template_kwargs)
            return tmpl.generate(*args, **kwargs)

        return error

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
            return app_log.error(f'url:{cls.name}.error is not a dict')
        # Compile all errors handlers
        cls.error = {}
        for error_code, error_config in error.items():
            try:
                error_code = int(error_code)
                if error_code < 100 or error_code > 1000:
                    raise ValueError()
            except ValueError:
                app_log.error(f'url.{cls.name}.error code {error_code} is not a number (100-1000)')
                continue
            if not isinstance(error_config, dict):
                return app_log.error(f'url:{cls.name}.error.{error_code} is not a dict')
            # Make a copy of the original. When we add headers, etc, it shouldn't affect original
            error_config = AttrDict(error_config)
            error_path, error_function = error_config.get('path'), error_config.get('function')
            if error_function:
                if error_path:
                    error_config.pop('path')
                    app_log.warning(
                        f'url.{cls.name}.error.{error_code} has function:. Ignoring path:')
                cls.error[error_code] = {'function': build_transform(
                    error_config,
                    vars=AttrDict((('status_code', None), ('kwargs', None), ('handler', None))),
                    filename=f'url:{cls.name}.error.{error_code}'
                )}
            elif error_path:
                encoding = error_config.get('encoding', 'utf-8')
                cls.error[error_code] = {'function': cls._error_fn(error_code, error_config)}
                mime_type, encoding = mimetypes.guess_type(error_path, strict=False)
                if mime_type:
                    error_config.setdefault('headers', {}).setdefault('Content-Type', mime_type)
            else:
                app_log.error(f'url.{cls.name}.error.{error_code} must have path: or function:')
            # Add the error configuration for reference
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
                self.session['_next_url'] = urljoin(self.xrequest_uri, next_url)
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
        try:
            import ipdb as pdb  # noqa: T100
        except ImportError:
            import pdb  # noqa: T100
            import warnings
            warnings.warn('"pip install ipdb" for better debugging')
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
                if isinstance(result, (str, bytes)):
                    self.write(result)
                else:
                    for item in result:
                        self.write(item)
                return
            except Exception:
                app_log.exception(f'url:{self.name}.error.{status_code} raised an exception')
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
        kwargs = dict(self._session_cookie)
        kwargs['expires_days'] = expires_days
        # Treat expiry: false as None, since expiry: null won't set null, it clears YAML
        if kwargs['expires_days'] is False:
            kwargs['expires_days'] = None
        # Use Secure cookies on HTTPS to prevent leakage into HTTP
        if self.request.protocol == 'https':
            kwargs['secure'] = True
        # Websockets cannot set cookies. They raise a RuntimeError. Ignore those.
        try:
            self.set_secure_cookie(self._session_cookie_id, session_id, **kwargs)
        except RuntimeError:
            pass
        # Warn if app.session.domain is x.com but request comes from y.com.
        host = self.request.host_name
        if ('domain' in kwargs and
                not host.endswith(kwargs['domain']) and
                not kwargs['domain'].endswith('.local')):
            app_log.warning(f'{self.name}: session.domain={kwargs["domain"]} '
                            f'but cookie sent to {host}')
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
        # If the expiry time is None, keep in the session store for 1 day
        store_expires = time.time() + (1 if expires_days is None else expires_days) * 24 * 60 * 60
        created_new_sid = False
        if getattr(self, '_session', None) is None:
            # Populate self._session based on the sid. If there's no sid cookie,
            # generate one and create an associated session object
            session_id = self.get_secure_cookie(self._session_cookie_id, max_age_days=9999999)
            # If there's no session id cookie "sid", create a random 32-char cookie
            if session_id is None:
                session_id = self._set_new_session_id(expires_days)
                created_new_sid = True
            # Convert bytes session to unicode before using
            session_id = session_id.decode('ascii')
            # If there's no stored session associated with it, create it
            self._session = self._session_store.load(session_id, {'_t': store_expires})
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
            s.update(id=new_sid, _t=store_expires)
            # Delete old contents. No _t also means expired
            self._session_store.dump(old_sid, {})

        return s

    def save_session(self):
        '''Persist the session object as a JSON'''
        if getattr(self, '_session', None) is not None:
            self._session_store.dump(self._session['id'], self._session)

    def otp(self, expire=60, prefix='otp', user=None):
        '''Return one-time password valid for ``expire`` seconds. Use with X-Gramex-OTP header'''
        user = self.current_user if user is None else user
        if not user:
            raise HTTPError(UNAUTHORIZED)
        nbits = 16
        otp = hexlify(os.urandom(nbits)).decode('ascii')
        self._session_store.dump(f'{prefix}:{otp}', {'user': user, '_t': time.time() + expire})
        return otp

    def apikey(self, expire=1e9, user=None):
        '''Return new API Key. To be used with the X-Gramex-Key header.'''
        return self.otp(expire=expire, prefix='key', user=user)

    def override_user(self):
        '''
        Use ``X-Gramex-User`` HTTP header to override current user for the session.
        Use ``X-Gramex-OTP`` HTTP header to set user based on OTP, or ``?gramex-otp=``.
        Use ``X-Gramex-Key`` HTTP header to set user based on API key, or ``?gramex-key=``.
        '''
        headers = self.request.headers
        cipher = headers.get('X-Gramex-User')
        if cipher:
            import json
            try:
                user = json.loads(decode_signed_value(
                    conf.app.settings['cookie_secret'], 'user', cipher,
                    max_age_days=self._session_expiry))
            except Exception:
                raise HTTPError(BAD_REQUEST, f'{self.name}: invalid X-Gramex-User: {cipher}')
            else:
                app_log.debug(f'{self.name}: Overriding user to {user!r}')
                self.session['user'] = user
                return
        # If valid OTP is specified, set the user from the API key
        otp = headers.get('X-Gramex-OTP') or self.get_argument('gramex-otp', None)
        if otp:
            otp_data = self._session_store.load('otp:' + otp, None)
            if not isinstance(otp_data, dict) or '_t' not in otp_data or 'user' not in otp_data:
                raise HTTPError(BAD_REQUEST, f'{self.name}: invalid Gramex OTP: {otp}')
            elif otp_data['_t'] < time.time():
                raise HTTPError(BAD_REQUEST, f'{self.name}: expired Gramex OTP: {otp}')
            self._session_store.dump(f'otp:{otp}', None)
            self.session['user'] = otp_data['user']
        # If API Key is specified, set the user from the API key
        key = headers.get('X-Gramex-Key') or self.get_argument('gramex-key', None)
        if key:
            key_data = self._session_store.load('key:' + key, None)
            if not isinstance(key_data, dict) or 'user' not in key_data:
                raise HTTPError(BAD_REQUEST, f'{self.name}: invalid Gramex Key: {key}')
            self.session['user'] = key_data['user']

    def set_last_visited(self):
        '''
        This method is called by :py:func:`BaseHandler.prepare` when any user
        accesses a page. It updates the last visited time in the ``_l`` session
        key. It does this only if the ``_i`` key exists.
        '''
        # For efficiency reasons, don't call get_session every time. Check
        # session only if there's a valid sid cookie (with possibly long expiry)
        if self.get_secure_cookie(self._session_cookie_id, max_age_days=9999999):
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
            key = (k if isinstance(k, bytes) else k.encode('latin-1')).decode('utf-8')
            # Invalid unicode (e.g. ?x=%f4) throws HTTPError. This disrupts even
            # error handlers. So if there's invalid unicode, log & continue.
            try:
                self.args[key] = self.get_arguments(k)
            except HTTPError:
                app_log.exception(f'Invalid URL argument {k}')

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

    def get_arg(self, name, default=..., first=False):
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
            if default is ...:
                raise MissingArgumentError(name)
            return default
        return self.args[name][0 if first else -1]

    def prepare(self):
        # If X-Request-URI is specified, use it. Else, when redirecting use RELATIVE URL. That
        # allows nginx to proxy_redirect Location headers
        self.xrequest_uri = self.request.headers.get('X-Request-URI', self.request.uri)
        # When passing to URL query parameters (e.g. /login/?next=), use the full URL
        self.xrequest_full_url = urljoin(self.request.full_url(), self.xrequest_uri)
        # For third-party redirection (e.g. Google Auth / Twitter needs a callback URI), then use
        # the full URL WITHOUT query parameters
        self.xredirect_uri = '{0.scheme:s}://{0.netloc:s}{0.path:s}'.format(
            urlsplit(self.xrequest_full_url))
        # If X-Gramex-Root is specified, treat that as the application's root URL
        self.gramex_root = self.request.headers.get('X-Gramex-Root', '').rstrip('/')
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
        # If specific methods are mentioned, authorize only if a mentioned method is used
        auth_methods = getattr(self, '_auth_methods', None)
        if auth_methods and self.request.method not in auth_methods:
            return
        # If CORS auth is specified, don't authorize for OPTIONS (pre-flight request)
        if self.request.method == 'OPTIONS' and getattr(self, '_cors', {}).get('auth'):
            return
        if not self.current_user:
            # Redirect non-AJAX requests GET/HEAD to login URL (if it's a string)
            ajax = self.request.headers.get('X-Requested-With', '').lower() == 'xmlhttprequest'
            if not ajax and self.request.method in ('GET', 'HEAD'):
                auth = getattr(self, '_auth', {})
                url = auth.get('login_url', self.gramex_root + self.get_login_url())
                # If login_url: false, don't redirect to a login URL. Only redirect if it's a URL
                if isinstance(url, str):
                    # Redirect to the login_url adding ?next=<X-Request-URI>
                    p = urlsplit(url)
                    q = parse_qsl(p.query)
                    q.append((auth.get('query', 'next'), self.xrequest_full_url))
                    target = urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), p.fragment))
                    self.redirect(target)
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

        args_type = str
        if len(args) > 0 and args[0] in (str, bytes, list, None):
            args_type, args = args[0], args[1:]

        for key in args:
            result[key] = self.get_argument(key, None)
            if result[key] is None:
                raise HTTPError(BAD_REQUEST, f'{key}: missing ?{key}=')
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
                    raise HTTPError(BAD_REQUEST, f'{key}: missing ?{name}=')

            # nargs: select the subset of items
            nargs = config.get('nargs', None)
            if isinstance(nargs, int):
                val = val[:nargs]
                if len(val) < nargs:
                    val += [''] * (nargs - len(val))
            elif nargs not in ('*', '+', None):
                raise ValueError(f'{key}: invalid nargs {nargs}')

            # convert to specified type
            newtype = config.get('type', None)
            if newtype is not None:
                newval = []
                for v in val:
                    try:
                        newval.append(newtype(v))
                    except ValueError:
                        raise HTTPError(
                            BAD_REQUEST, f'{key}: type error ?{name}={v} to {newtype!r}')
                val = newval

            # choices: check valid items
            choices = config.get('choices', None)
            if isinstance(choices, (list, dict, set)):
                choices = set(choices)
                for v in val:
                    if v not in choices:
                        raise HTTPError(BAD_REQUEST, f'{key}: invalid choice ?{name}={v}')

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
        elif args_type in (str, bytes):
            for key, val in self.args.items():
                if key not in args and key not in kwargs:
                    result[key] = args_type(val[0])

        return result

    def create_template_loader(self, template_path):
        settings = self.application.settings
        return CacheLoader(template_path, autoescape=settings['autoescape'],
                           whitespace=settings.get('template_whitespace', None))


class BaseWebSocketHandler(WebSocketHandler, BaseMixin):
    def initialize(self, **kwargs):
        self._session, self._session_json = None, 'null'
        if self.cache:
            self.cachefile = self.cache()
            self.original_get = self.get
            self.get = self._cached_get
        if self._set_xsrf:
            self.xsrf_token

    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        for method in self._on_init_methods:
            method(self)
        yield super(BaseWebSocketHandler, self).get(*args, **kwargs)

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


class SetupFailedHandler(RequestHandler, BaseMixin):
    '''
    Reports that the setup() operation has failed.

    Used by gramex.services.init() when setting up URLs. If it's not able to set
    up a handler, it replaces it with this handler.
    '''
    def get(self):
        six.reraise(*self.exc_info)


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
        handle_cache[path] = io.open(path, 'a', encoding='utf-8')
    return handle_cache[path]
