from __future__ import unicode_literals

import os
import json
import atexit
import functools
import tornado.gen
from textwrap import dedent
from binascii import b2a_base64
from orderedattrdict import AttrDict, DefaultAttrDict
from six.moves.urllib_parse import urlparse, urlsplit, urlencode
from tornado.log import access_log
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
    def setup(cls, transform={}, redirect={}, auth=None, log={}, set_xsrf=None, **kwargs):
        '''
        One-time setup for all request handlers. This is called only when
        gramex.yaml is parsed / changed.
        '''
        cls._on_finish_methods = []

        cls.setup_transform(transform)
        cls.setup_redirect(redirect)
        cls.setup_auth(auth)
        cls.setup_session(conf.app.get('session'))
        cls.setup_log(log or objectpath(conf, 'handlers.BaseHandler.log'))
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
                    filename='url>%s' % cls.name),
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
        cls.redirects = []
        for key, value in redirect.items():
            if key == 'query':
                cls.redirects.append(lambda h, v=value: h.get_argument(v, None))
            elif key == 'header':
                cls.redirects.append(lambda h, v=value: h.request.headers.get(v))
            elif key == 'url':
                cls.redirects.append(lambda h, v=value: v)
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
            # Wrap available methods via an @authorized decorator
            for method in auth.get('method', ['get', 'post', 'put', 'delete', 'patch']):
                func = getattr(cls, method)
                if callable(func):
                    setattr(cls, method, authorized(func))

            cls.permissions = []
            if auth.get('condition'):
                cls.permissions.append(
                    build_transform(auth['condition'], vars=AttrDict(handler=None),
                                    filename='url>%s.auth.permission' % cls.name))
            for keypath, values in auth.get('membership', {}).items():
                cls.permissions.append(check_membership(keypath, values))

    @classmethod
    def setup_log(cls, log):
        if log is None or (isinstance(log, dict) and 'format' not in log):
            return
        params = DefaultAttrDict(int)
        try:
            log['format'] % params
        except (TypeError, ValueError):
            app_log.error('Invalid log.format: %s', log['format'])
            return
        direct_vars = {
            'method': 'handler.request.method',
            'uri': 'handler.request.uri',
            'ip': 'handler.request.remote_ip',
            'status': 'handler.get_status()',
            'duration': 'handler.request.request_time() * 1000',
            'size': 'handler.get_content_size()',
            'user': 'handler.current_user or ""',
            'session': 'handler.session.get("id", "")',
        }
        object_vars = {
            'args': 'handler.get_argument("%(key)s")',
            'headers': 'handler.request.headers.get("%(key)s")',
            'cookies': 'handler.request.cookies["%(key)s"].value ' +
                       'if "%(key)s" in request.cookies else ""',
            'env': 'os.environ.get("%(key)s", "")',
        }
        code = dedent('''
            def log_request(handler):
                obj = {}
                status = obj['status'] = handler.get_status()
            %s
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
                    obj.append('    obj["%s"] = %s' % (key, object_vars[prefix] % {'key': key}))
                    continue
            app_log.error('Unknown key %s in log.format: %s', key, log['format'])
            return

        context = {
            'log_format': log['format'],
            'access_log': access_log,
        }
        code = compile(code % '\n'.join(obj), filename='url:' + cls.name, mode='exec')
        exec(code, context)
        cls.log_request = context['log_request']

    def initialize(self, **kwargs):
        self.kwargs = kwargs
        self._session, self._session_json = None, 'null'
        if self.cache:
            self.cachefile = self.cache()
            self.original_get = self.get
            self.get = self._cached_get
        if self._set_xsrf:
            self.xsrf_token

    def set_default_headers(self):
        self.set_header('Server', server_header)

    def save_redirect_page(self):
        '''
        Loop through all redirect: methods and save the first available redirect
        page against the session. Defaults to previously set value, else '/'.
        '''
        for method in self.redirects:
            next_url = method(self)
            if next_url:
                self.session['_next_url'] = next_url
                return
        self.session.setdefault('_next_url', '/')

    def redirect_next(self):
        self.redirect(self.session.pop('_next_url', '/'))

    @tornado.gen.coroutine
    def _cached_get(self, *args, **kwargs):
        cached = self.cachefile.get()
        headers_written = set()
        if cached is not None:
            self.set_status(cached['status'])
            for name, value in cached['headers']:
                if name in headers_written:
                    self.add_header(name, value)
                else:
                    self.set_header(name, value)
                    headers_written.add(name)
            self.write(cached['body'])
        else:
            self.cachefile.wrap(self)
            yield self.original_get(*args, **kwargs)

    def get_current_user(self):
        return self.session.get('user')

    def debug_exception(self, typ, value, tb):
        super(BaseHandler, self).log_exception(typ, value, tb)
        import ipdb as pdb
        pdb.post_mortem(tb)

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


class KeyStore(object):
    '''
    Base class for persistent dictionaries. (But KeyStore is not persistent.)

        >>> store = KeyStore(path)
        >>> value = store.load(key, None)
        >>> store.dump(key, value)
        >>> store.close()
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
        pass

    def close(self):
        '''Flush and close all open handles'''
        pass


class HDF5Store(KeyStore):
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
        self.store.close()


class JSONStore(KeyStore):
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


def authorized(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        # If the user is not authenticated, get them to log in.
        # This section is identical to @tornado.web.authenticated
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

        # Run the method if the user is authenticated and authorized
        return method(self, *args, **kwargs)

    return wrapper


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
