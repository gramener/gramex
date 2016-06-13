'''
The CacheFile object exposes a get, wrap and close interface to handlers.

- ``.get()`` reads all data against the key
- ``.wrap(handler)`` is used to wrap the ``.write()`` method to append into a
  write queue, and the ``.on_finish()`` method to save the result.

Each type of store has a separate CacheFile. (MemoryCacheFile, DiskCacheFile,
etc.) The parent CacheFile implements the no-caching behaviour.

See gramex.handlers.BaseHandler for examples on how to use these objects.
'''
from __future__ import unicode_literals

import json
from six.moves import cPickle
from diskcache import Cache as DiskCache
from .ttlcache import TTLCache as MemoryCache
from gramex.config import app_log

# HTTP Headers that should not be cached
ignore_headers = {
    # Do not cache headers referenced anywhere in tornado.http1connection
    'Content-Encoding', 'Vary', 'Transfer-Encoding', 'Expect',
    'Keep-Alive', 'Connection', 'X-Consumed-Content-Encoding',
    # Do not cache things that SHOULD or WILL be recomputed anyway
    'Date',             # This is the current date, not the Last-Modified date
    'Server',           # Always show Gramex/version
    'Etag',             # Automatically added by Tornado
    'Content-Length',   # Automatically added by Tornado
}


def get_cachefile(store):
    if isinstance(store, MemoryCache):
        return MemoryCacheFile
    elif isinstance(store, DiskCache):
        return DiskCacheFile
    else:
        app_log.warn('cache: ignoring unknown store %s', store)
        return CacheFile

# In Python 3, json does not support byte encoding. Use pickle instead. (It's faster in Pythom 3)
try:
    json.dumps(b'')
    dumps, loads = json.dumps, json.loads
except TypeError:
    dumps, loads = cPickle.dumps, cPickle.loads


class CacheFile(object):

    def __init__(self, key, store, handler, expire=None, statuses=None):
        self.key = key
        self.store = store
        self.handler = handler
        self.expire = expire
        self.statuses = statuses

    def get(self):
        return None

    def wrap(self, handler):
        return handler


class MemoryCacheFile(CacheFile):
    def get(self):
        result = self.store.get(self.key)
        return None if result is None else loads(result)

    def wrap(self, handler):
        self._write_buffer = []
        self._write = handler.write
        self._on_finish = handler.on_finish

        def write(chunk):
            self._write(chunk)
            self._write_buffer.append(handler._write_buffer[-1])

        def on_finish():
            # Cache contents only for HTTP 200 responses
            if handler.get_status() in self.statuses:
                self.store.set(
                    key=self.key,
                    value=dumps({
                        'status': handler._status_code,
                        'headers': [
                            [name, value] for name, value in handler._headers.get_all()
                            if name not in ignore_headers
                        ],
                        'body': b''.join(self._write_buffer)
                    }),
                    expire=self.expire,
                )
            self._on_finish()

        handler.write = write
        handler.on_finish = on_finish


class DiskCacheFile(MemoryCacheFile):
    'Identical interface to MemoryCacheFile'
    pass
