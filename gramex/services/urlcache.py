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
    if store.__class__.__module__.startswith('cachetools'):
        return MemoryCacheFile
    elif store.__class__.__module__.startswith('diskcache'):
        return DiskCacheFile
    else:
        return CacheFile


class CacheFile(object):

    def __init__(self, key, store, handler):
        self.key = key
        self.store = store
        self.handler = handler

    def get(self):
        return None

    def wrap(self, handler):
        return handler


class MemoryCacheFile(CacheFile):
    def get(self):
        result = self.store.get(self.key)
        return None if result is None else json.loads(result)

    def wrap(self, handler):
        self._write_buffer = []
        self._write = handler.write
        self._on_finish = handler.on_finish

        def write(chunk):
            self._write(chunk)
            self._write_buffer.append(handler._write_buffer[-1])

        def on_finish():
            self.store[self.key] = json.dumps({
                'status': handler._status_code,
                'headers': [
                    [name, value] for name, value in handler._headers.get_all()
                    if name not in ignore_headers
                ],
                'body': b''.join(self._write_buffer)
            })
            self._on_finish()

        handler.write = write
        handler.on_finish = on_finish


class DiskCacheFile(MemoryCacheFile):
    'Identical interface to MemoryCacheFile'
    pass
