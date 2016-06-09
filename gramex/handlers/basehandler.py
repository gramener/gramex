from __future__ import unicode_literals

import os
import json
import atexit
import functools
import tornado.gen
from binascii import b2a_base64
from orderedattrdict import AttrDict
from six.moves.http_client import FORBIDDEN
from six.moves.urllib_parse import urlparse, urlsplit, urlencode
from tornado.web import RequestHandler, HTTPError
from .. import conf, __version__
from ..transforms import build_transform

server_header = 'Gramex/%s' % __version__
session_store_cache = {}


class BaseHandler(RequestHandler):
    '''
    BaseHandler provides auth, caching and other services common to all request
    handlers. All RequestHandlers must inherit from BaseHandler.
    '''
    @classmethod
    def setup(cls, transform={}, redirect={}, auth=None, **kwargs):
        '''
        One-time setup for all request handlers. This is called only when
        gramex.yaml is parsed / changed.
        '''
        cls._on_finish_methods = []

        # transform: sets up transformations on ouput that some handlers use
        cls.transform = {}
        for pattern, trans in transform.items():
            cls.transform[pattern] = {
                'function': build_transform(
                    trans, vars=AttrDict((('content', None), ('handler', None))),
                    filename='url>%s' % cls.name),
                'headers': trans.get('headers', {}),
                'encoding': trans.get('encoding'),
            }

        # app.debug.exception enables debugging exceptions using pdb
        debug_conf = conf.app.get('debug')
        if debug_conf and debug_conf.get('exception', False):
            cls.log_exception = cls.debug_exception

        # app.session: sets up session handling.
        # handler.session returns the session object. It is saved on finish.
        session_conf = conf.app.get('session')
        if session_conf is not None:
            key = store_type, store_path = session_conf.get('type'), session_conf.get('path')
            if key not in session_store_cache:
                if store_type == 'memory':
                    session_store_cache[key] = KeyStore(store_path)
                elif store_type == 'json':
                    session_store_cache[key] = JSONStore(store_path)
                elif store_type == 'hdf5':
                    session_store_cache[key] = HDF5Store(store_path)
                else:
                    raise NotImplementedError('Session type: %s not implemented' % store_type)
            cls._session_store = session_store_cache[key]
            cls.session = property(cls.get_session)
            cls._session_days = session_conf.get('expiry')
            cls._on_finish_methods.append(cls.save_session)

        # redirect: sets up redirect methods
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

    def initialize(self, **kwargs):
        self.kwargs = kwargs
        self._session, self._session_json = None, 'null'
        if self.cache:
            self.cachefile = self.cache()
            self.original_get = self.get
            self.get = self._cached_get

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

        The session object is an AttrDict. Ensure that it contains JSON
        serializable objects.
        '''
        if getattr(self, '_session', None) is None:
            session_id = self.get_secure_cookie('sid', max_age_days=self._session_days)
            # If there's no session id cookie "sid", create a random 32-char cookie
            if session_id is None:
                session_id = b2a_base64(os.urandom(24))[:-1]
                self.set_secure_cookie('sid', session_id, expires_days=self._session_days)
            session_id = session_id.decode('ascii')
            # The session data is stored as JSON. Load it. If missing, use an empty AttrDict
            self._session_json = self._session_store.load(session_id, '{}')
            self._session = json.loads(self._session_json, object_pairs_hook=AttrDict)
            # Overwrite the .id to the session ID even if a handler has changed it
            self._session.id = session_id
        return self._session

    def save_session(self):
        '''Persist the session object as a JSON'''
        if getattr(self, '_session', None) is None:
            return
        # If the JSON representation of the session object has changed, save it
        session_json = json.dumps(self._session, ensure_ascii=True, separators=(',', ':'))
        if session_json != self._session_json:
            self._session_store.dump(self._session.id, session_json)
            self._session_json = session_json

    def on_finish(self):
        # Loop through class-level callbacks
        for callback in self._on_finish_methods:
            callback(self)


class KeyStore(object):
    def __init__(self, path):
        self.path = os.path.abspath(path)
        folder = os.path.dirname(self.path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.store = {}
        atexit.register(self.close)

    def load(self, key, default=None):
        return self.store.get(key, default)

    def dump(self, key, value):
        self.store[key] = value

    def close(self):
        pass


class HDF5Store(KeyStore):
    def __init__(self, path):
        super(HDF5Store, self).__init__(path)
        import h5py
        self.store = h5py.File(self.path, 'a')

    def load(self, key, default=None):
        result = self.store.get(key, default)
        return result.value if hasattr(result, 'value') else result

    def dump(self, key, value):
        if key in self.store:
            del self.store[key]
        self.store[key] = value

    def close(self):
        self.store.close()


class JSONStore(KeyStore):
    def __init__(self, path):
        super(JSONStore, self).__init__(path)
        try:
            self.handle = open(self.path, 'r+')     # noqa: no encoding for json
            self.store = json.load(self.handle)
        except (IOError, ValueError):
            self.handle = open(self.path, 'w')      # noqa: no encoding for json
            self.store = {}

    def close(self):
        self.handle.seek(0)
        json.dump(self.store, self.handle, ensure_ascii=True, separators=(',', ':'))
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


def objectpath(node, keypath):
    for key in keypath.split('.'):
        if key in node:
            node = node[key]
        else:
            return None
    return node
