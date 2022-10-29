'''
The CacheFile object exposes a get, wrap and close interface to handlers.

- ``.get()`` reads all data against the key
- ``.wrap(handler)`` is used to wrap the ``.write()`` method to append into a
  write queue, and the ``.on_finish()`` method to save the result.

Each type of store has a separate CacheFile. (MemoryCacheFile, DiskCacheFile,
etc.) The parent CacheFile implements the no-caching behaviour.

See gramex.handlers.BaseHandler for examples on how to use these objects.
'''
# B403:import_public we only pickle Gramex internal objects
import pickle  # nosec B403
from diskcache import Cache as DiskCache
from .ttlcache import TTLCache as MemoryCache
from .rediscache import RedisCache
from gramex.config import app_log
from gramex.http import OK, NOT_MODIFIED

# HTTP Headers that should not be cached
ignore_headers = {
    # Do not cache headers referenced anywhere in tornado.http1connection
    'Content-Encoding',
    'Vary',
    'Transfer-Encoding',
    'Expect',
    'Keep-Alive',
    'Connection',
    'X-Consumed-Content-Encoding',
    # Do not cache things that SHOULD or WILL be recomputed anyway
    'Date',  # This is the current date, not the Last-Modified date
    'Server',  # Always show Gramex/version
    'Etag',  # Automatically added by Tornado
    'Content-Length',  # Automatically added by Tornado
}


def get_cachefile(store):
    if isinstance(store, MemoryCache):
        return MemoryCacheFile
    elif isinstance(store, DiskCache):
        return DiskCacheFile
    elif isinstance(store, RedisCache):
        return RedisCacheFile
    else:
        app_log.warning(f'cache: ignoring unknown store {store}')
        return CacheFile


class CacheFile:
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
        # B301:pickle key is an internal state string and safe to pickle
        return None if result is None else pickle.loads(result)  # nosec B301

    def wrap(self, handler):
        self._finish = handler.finish

        def finish(chunk=None):
            # Save the headers and body originally written
            headers = [
                [name, value]
                for name, value in handler._headers.get_all()
                if name not in ignore_headers
            ]
            body = b''.join(handler._write_buffer)

            # Call the original finish
            self._finish(chunk)

            # Cache headers and body (only for allowed HTTP responses)
            status = handler.get_status()
            if status in self.statuses:
                self.store.set(
                    key=self.key,
                    value=pickle.dumps(
                        {
                            'status': OK if status == NOT_MODIFIED else status,
                            'headers': headers,
                            'body': body,
                        },
                        pickle.HIGHEST_PROTOCOL,
                    ),
                    expire=self.expire,
                )

        handler.finish = finish


class DiskCacheFile(MemoryCacheFile):
    '''Identical interface to MemoryCacheFile'''

    pass


class RedisCacheFile(CacheFile):
    def get(self):
        return self.store.get(self.key)

    def wrap(self, handler):
        self._finish = handler.finish

        def finish(chunk=None):
            # Save the headers and body originally written
            headers = [
                [name, value]
                for name, value in handler._headers.get_all()
                if name not in ignore_headers
            ]
            body = b''.join(handler._write_buffer)

            # Call the original finish
            self._finish(chunk)

            # Cache headers and body (only for allowed HTTP responses)
            status = handler.get_status()
            if status in self.statuses:
                self.store.set(
                    key=self.key,
                    value={
                        'status': OK if status == NOT_MODIFIED else status,
                        'headers': headers,
                        'body': body,
                    },
                    expire=self.expire,
                )

        handler.finish = finish
