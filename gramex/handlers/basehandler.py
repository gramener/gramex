from __future__ import unicode_literals

import io
import os
import json
import atexit
import mimetypes
import functools
import tornado.gen
from textwrap import dedent
from types import GeneratorType
from binascii import b2a_base64
from orderedattrdict import AttrDict, DefaultAttrDict
from six.moves.urllib_parse import urlparse, urlsplit, urljoin, urlencode
from tornado.log import access_log
from tornado.template import Template
from tornado.web import RequestHandler, HTTPError
from gramex import conf, __version__
from gramex.config import objectpath, app_log
from gramex.transforms import build_transform

server_header = 'Gramex/%s' % __version__
session_store_cache = {}
FORBIDDEN = 403


class BaseHandler(RequestHandler):
    '''
    BaseHandler provides auth, caching and other services common to all request
    handlers. All RequestHandlers must inherit from BaseHandler.
    '''
    @classmethod
    def setup(cls, transform={}, redirect={}, auth=None, log={}, set_xsrf=None,
              error=None, **kwargs):
        '''
        One-time setup for all request handlers. This is called only when
        gramex.yaml is parsed / changed.
        '''
        cls._on_init_methods = []
        cls._on_finish_methods = []

        cls.setup_transform(transform)
        cls.setup_redirect(redirect)
        cls.setup_auth(auth)
        cls.setup_session(conf.app.get('session'))
        cls.setup_log(log or objectpath(conf, 'handlers.BaseHandler.log'))
        cls.setup_error(error)
        cls._set_xsrf = set_xsrf

        # app.settings.debug enables debugging exceptions using pdb
        if conf.app.settings.get('debug', False):
            cls.log_exception = cls.debug_exception

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

    @classmethod
    def setup_session(cls, session_conf):
        '''handler.session returns the session object. It is saved on finish.'''
        if session_conf is None:
            return
        key = store_type, store_path = session_conf.get('type'), session_conf.get('path')
        flush = session_conf.get('flush')
        if key not in session_store_cache:
            if store_type == 'memory':
                session_store_cache[key] = KeyStore(store_path, flush=flush)
            elif store_type == 'json':
                session_store_cache[key] = JSONStore(store_path, flush=flush)
            elif store_type == 'hdf5':
                session_store_cache[key] = HDF5Store(store_path, flush=flush)
            else:
                raise NotImplementedError('Session type: %s not implemented' % store_type)
        cls._session_store = session_store_cache[key]
        cls.session = property(cls.get_session)
        cls._session_days = session_conf.get('expiry')
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

        When any BaseHandler subclass calls ``self.save_redirect_page()``, it
        stores the redirect URL in ``session['_next_url']``. The URL is
        calculated relative to the handler's URL.

        After that, when the subclass calls ``self.redirect_next()``, it
        redirects to ``session['_next_url']`` and clears the value. (If the
        ``_next_url`` was not stored, we redirect to the home page ``/``.)

        Only some handlers implement redirection. But they all implement it in
        this same consistent way.
        '''
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
                        source = urlparse(handler.request.uri)
                        if source.scheme == target.scheme and source.netloc == target.netloc:
                            return next_uri
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
            cls._on_init_methods.append(cls.authorize)
            cls.permissions = []
            if auth.get('condition'):
                cls.permissions.append(
                    build_transform(auth['condition'], vars=AttrDict(handler=None),
                                    filename='url:%s.auth.permission' % cls.name))
            for keypath, values in auth.get('membership', {}).items():
                cls.permissions.append(check_membership(keypath, values))

    @classmethod
    def setup_log(cls, log):
        if log is None:
            return
        if not isinstance(log, dict) or 'format' not in log:
            app_log.error('url:%s.log is not a dict with a format key', cls.name)
            return
        params = DefaultAttrDict(int)
        try:
            log['format'] % params
        except (TypeError, ValueError):
            app_log.error('url:%s.log.format invalid: %s', cls.name, log['format'])
            return
        direct_vars = {
            'method': 'handler.request.method',
            'uri': 'handler.request.uri',
            'ip': 'handler.request.remote_ip',
            'status': 'handler.get_status()',
            'duration': 'handler.request.request_time() * 1000',
            # TODO: get_content_size() is not available in RequestHandler
            # 'size': 'handler.get_content_size()',
            'user': 'handler.current_user or ""',
            'session': 'handler.session.get("id", "")',
        }
        object_vars = {
            'args': 'handler.get_argument("%(value)s", "")',
            'headers': 'handler.request.headers.get("%(value)s", "")',
            'cookies': 'handler.request.cookies["%(value)s"].value ' +
                       'if "%(value)s" in handler.request.cookies else ""',
            'user': '(handler.current_user or {}).get("%(value)s", "")',
            'env': 'os.environ.get("%(value)s", "")',
        }
        code = dedent('''
            def log_request(handler, log_method=None):
                obj = {}
                status = obj['status'] = handler.get_status()
            %s
                if log_method is None:
                    if status < 400:
                        log_method = access_log.info
                    elif status < 500:
                        log_method = access_log.warning
                    else:
                        log_method = access_log.error
                log_method(log_format %% obj)
        ''')
        obj = []
        for key in params:
            if key in direct_vars:
                obj.append('    obj["%s"] = %s' % (key, direct_vars[key]))
                continue
            if '.' in key:
                prefix, value = key.split('.', 2)
                if prefix in object_vars:
                    obj.append('    obj["%s"] = %s' % (key, object_vars[prefix] % {
                        'key': key,
                        'prefix': prefix,
                        'value': value,
                    }))
                    continue
            app_log.error('Skipping unknown key %s in log.format: %s', key, log['format'])

        context = {
            'log_format': log['format'],
            'access_log': access_log,
            'os': os,
        }
        code = compile(code % '\n'.join(obj), filename='url:' + cls.name, mode='exec')
        exec(code, context)
        cls.log_request = context['log_request']

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
            app_log.error('url:%s.error is not a dict', cls.name)
            return
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
                app_log.error('url:%s.error.%d is not a dict', cls.name, error_code)
                return
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
                # TODO: every time the template changes, recompile it. Add watch, remove old watch
                with io.open(error_config['path'], 'r', encoding=encoding) as handle:
                    cls.error[error_code] = {
                        'function': Template(handle.read(), **template_kwargs).generate
                    }
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

    def initialize(self, **kwargs):
        self.kwargs = kwargs
        self._session, self._session_json = None, 'null'
        if self.cache:
            self.cachefile = self.cache()
            self.original_get = self.get
            self.get = self._cached_get
        if self._set_xsrf:
            self.xsrf_token

    def prepare(self):
        for method in self._on_init_methods:
            method(self)

    def set_default_headers(self):
        self.set_header('Server', server_header)

    def save_redirect_page(self):
        '''
        Loop through all redirect: methods and save the first available redirect
        page against the session. Defaults to previously set value, else ``/``.

        See :func:setup_redirect
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

        See :func:setup_redirect
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
            if name in headers_written:
                self.add_header(name, value)
            else:
                self.set_header(name, value)
                headers_written.add(name)

    def get_current_user(self):
        return self.session.get('user')

    def debug_exception(self, typ, value, tb):
        super(BaseHandler, self).log_exception(typ, value, tb)
        import ipdb as pdb
        pdb.post_mortem(tb)

    def _write_custom_error(self, status_code, **kwargs):
        if status_code in self.error:
            try:
                result = self.error[status_code]['function'](
                    status_code=status_code, kwargs=kwargs, handler=self)
                self._write_headers(self.error[status_code]['conf'].get('headers', {}).items())
                # result may be a generator / tuple from build_transform,
                # or a str from Template.generate. Handle either case
                if isinstance(result, (GeneratorType, tuple)):
                    for item in result:
                        self.write(item)
                else:
                    self.write(result)
                return
            except Exception:
                app_log.exception('url:%s.error.%d error handler raised an exception:' %
                                  (self.name, status_code))
        # If error was not written, use the default error
        self._write_error(status_code, **kwargs)

    @property
    def session(self):
        raise NotImplementedError('Specify a session: section in gramex.yaml')

    def get_session(self):
        '''
        Return the session object for the cookie "sid" value. If no "sid" cookie
        exists, set up a new one. If no session object exists for the sid,
        create it. By default, the session object contains a "id" holding the
        "sid" value.

        The session is a dict. You must ensure that it is JSON serializable.
        '''
        if getattr(self, '_session', None) is None:
            session_id = self.get_secure_cookie('sid', max_age_days=self._session_days)
            # If there's no session id cookie "sid", create a random 32-char cookie
            if session_id is None:
                session_id = b2a_base64(os.urandom(24))[:-1]
                self.set_secure_cookie('sid', session_id, expires_days=self._session_days)
            session_id = session_id.decode('ascii')
            self._session = self._session_store.load(session_id, {})
            # Overwrite id to the session ID even if a handler has changed it
            self._session['id'] = session_id
        return self._session

    def save_session(self):
        '''Persist the session object as a JSON'''
        if getattr(self, '_session', None) is not None:
            self._session_store.dump(self._session['id'], self._session)

    def on_finish(self):
        # Loop through class-level callbacks
        for callback in self._on_finish_methods:
            callback(self)

    def authorize(self):
        if not self.current_user:
            if self.request.method in ('GET', 'HEAD'):
                url = self.get_login_url()
                if '?' not in url:
                    if urlsplit(url).scheme:
                        # if login url is absolute, make next absolute too
                        next_url = self.request.full_url()
                    else:
                        next_url = self.request.uri
                    url += '?' + urlencode(dict(next=next_url))
                self.redirect(url)
                return
            raise HTTPError(FORBIDDEN)

        # If the user is not authorized, display a template or raise error
        for permit_generator in self.permissions:
            for result in permit_generator(self):
                if not result:
                    template = self.conf.kwargs.auth.get('template')
                    if template:
                        self.render(template)
                        return
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

    When the program exits, ``.close()`` is automatically called.
    '''
    def __init__(self, path, flush=None):
        '''Initialise the KeyStore at path'''
        # Ensure that path directory exists
        self.path = os.path.abspath(path)
        folder = os.path.dirname(self.path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.store = {}
        # Periodically flush buffers
        if flush is not None:
            tornado.ioloop.PeriodicCallback(self.flush, callback_time=flush).start()
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
        raise NotImplementedError()

    def close(self):
        '''Flush and close all open handles'''
        raise NotImplementedError()


class HDF5Store(KeyStore):
    '''
    A KeyStore that stores data in a HDF5 file. Typical usage::

        >>> store = HDF5Store('file.h5', flush=15)
        >>> value = store.load(key)
        >>> store.dump(key, value)
    '''
    def __init__(self, path, *args, **kwargs):
        super(HDF5Store, self).__init__(path, *args, **kwargs)
        import h5py
        self.store = h5py.File(self.path, 'a')

    def load(self, key, default=None):
        result = self.store.get(key, None)
        if result is None:
            return default
        json_value = result.value if hasattr(result, 'value') else result
        return json.loads(json_value, object_pairs_hook=AttrDict)

    def dump(self, key, value):
        if key in self.store:
            del self.store[key]
        self.store[key] = json.dumps(value, ensure_ascii=True, separators=(',', ':'))

    def flush(self):
        self.store.flush()

    def close(self):
        try:
            self.store.close()
        # h5py.h5f.get_obj_ids often raises a ValueError: Not a file id.
        # This is presumably if the file handle has been closed. Log & ignore.
        except ValueError:
            app_log.warning('HDF5Store("%s").close() error ignored', self.path)


class JSONStore(KeyStore):
    '''
    A KeyStore that stores data in a JSON file. Typical usage::

        >>> store = JSONStore('file.h5', flush=15)
        >>> value = store.load(key)
        >>> store.dump(key, value)

    This is less efficient than HDF5Store for large data, but is human-readable.
    '''
    def __init__(self, path, *args, **kwargs):
        super(JSONStore, self).__init__(path, *args, **kwargs)
        try:
            self.handle = open(self.path, 'r+')     # noqa: no encoding for json
            self.store = json.load(self.handle)
        except (IOError, ValueError):
            self.handle = open(self.path, 'w')      # noqa: no encoding for json
            self.store = {}

    def flush(self):
        self.handle.seek(0)
        json.dump(self.store, self.handle, ensure_ascii=True, separators=(',', ':'))

    def close(self):
        self.flush()
        self.handle.close()


def check_membership(keypath, values):
    values = set(values) if isinstance(values, list) else set([values])

    def ismember(self):
        node = objectpath(self.session.get('user', {}), keypath)
        if node is None:
            yield False
        elif isinstance(node, list):
            yield len(set(node) & values) > 0
        else:
            yield node in values
    return ismember
