from __future__ import unicode_literals

import os
import json
import atexit
import tornado.gen
from binascii import b2a_base64
from orderedattrdict import AttrDict
from tornado.web import RequestHandler
from tornado.escape import json_decode
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
    def setup(cls, transform={}, **kwargs):
        cls.transform = {}
        cls._on_finish_class = []
        for pattern, trans in transform.items():
            cls.transform[pattern] = {
                'function': build_transform(
                    trans, vars=AttrDict((('content', None), ('handler', None))),
                    filename='url>%s' % cls.name),
                'headers': trans.get('headers', {}),
                'encoding': trans.get('encoding'),
            }

        # Set up debug handling
        debug_conf = conf.app.get('debug')
        if debug_conf and debug_conf.get('exception', False):
            cls.log_exception = cls.debug_exception

        # If gramex.yaml has a session: section, set up session handling.
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
            cls._on_finish_class.append(cls.save_session)

    def initialize(self, **kwargs):
        self.kwargs = kwargs
        self._session, self._session_json = None, 'null'
        if self.cache:
            self.cachefile = self.cache()
            self.original_get = self.get
            self.get = self._cached_get

    def set_default_headers(self):
        self.set_header('Server', server_header)

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
        app_auth = conf.app.settings.get('auth', False)
        route_auth = self.kwargs.get('auth', app_auth)
        if not route_auth:
            return 'static'
        user_json = self.get_secure_cookie('user')
        if not user_json:
            return None
        return json_decode(user_json)

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
        if self._session is None:
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
        if self._session is None:
            return
        # If the JSON representation of the session object has changed, save it
        session_json = json.dumps(self._session, ensure_ascii=True, separators=(',', ':'))
        if session_json != self._session_json:
            self._session_store.dump(self._session.id, session_json)
            self._session_json = session_json

    def on_finish(self):
        # Loop through class-level callbacks
        for callback in self._on_finish_class:
            callback(self)


class KeyStore(object):
    def __init__(self, path):
        self.path = path
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
