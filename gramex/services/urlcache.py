'''
The CacheFile object exposes a get, wrap and close interface to handlers.

- ``.get()`` reads all data against the key
- ``.wrap(method)`` is used to wrap the `.write()` method to append into a write queue
- ``.close()`` flushes the write queue into the relevant store

Each type of store has a separate CacheFile. (MemoryCacheFile, DiskCacheFile,
etc.) The parent CacheFile implements the no-caching behaviour.

See gramex.handlers.BaseHandler for examples on how to use these objects.
'''
from __future__ import unicode_literals


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

    def wrap(self, method):
        return method

    def close(self):
        pass


class MemoryCacheFile(CacheFile):
    def get(self):
        return self.store.get(self.key)

    def wrap(self, handler):
        self._write_buffer = []
        self._write = handler.write
        self._on_finish = handler.on_finish

        def write(chunk):
            self._write(chunk)
            self._write_buffer.append(handler._write_buffer[-1])

        def on_finish():
            self.store[self.key] = b''.join(self._write_buffer)
            self._on_finish()

        handler.write = write
        handler.on_finish = on_finish


class DiskCacheFile(MemoryCacheFile):
    'Identical interface to MemoryCacheFile'
    pass
