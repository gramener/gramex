# B403:import_public we only pickle Gramex internal objects
import pickle  # nosec B403
from redis import StrictRedis


def get_redis(path: str, **kwargs):
    host, port, db, redis_kwargs = 'localhost', 6379, 0, {}
    if isinstance(path, str):
        parts = path.split(':')
        if parts:
            host = parts.pop(0)
        if parts:
            port = int(parts.pop(0))
        if parts:
            db = int(parts.pop(0))
        redis_kwargs = dict(part.split('=', 1) for part in parts)
    for key, val in kwargs.items():
        redis_kwargs.setdefault(key, val)
    return StrictRedis(host=host, port=port, db=db, **redis_kwargs)


class RedisCache:
    '''
    LRU Cache that stores data in a Redis database. Typical usage::

        >>> store = RedisCache('localhost:6379:1:password=x:...', 500000) # host:port:db:params
        >>> value = store.get(key)
        >>> store.set(key, value, expire)

    The path in the constructor contains parameters separated by colon (:):

    - `host`: the Redis server location (default: localhost)
    - `port`: the Redis server port (default: 6379)
    - `db`: the Redis server DB number (default: 0)
    - zero or more parameters passed to StrictRedis (e.g. password=abc)

    `maxsize` defines the maximum limit of cache. This will set maxmemory for the redis instance
    and not specific to a db. If it's false-y (None, 0, etc.) no limit is set.

    Both Keys and Values are stored as pickle dump.
    This is an approximate LRU implementation. Read more here.(https://redis.io/topics/lru-cache)
    '''

    def __init__(self, path=None, maxsize=None, *args, **kwargs):
        self.store = get_redis(path, decode_responses=False)
        self.size = 0
        if maxsize:
            if self.currsize > maxsize:
                self.flush()
            self.store.config_set('maxmemory', maxsize)
            self.store.config_set('maxmemory-policy', 'allkeys-lru')  # Approximate LRU cache

    def __getitem__(self, key):
        key = pickle.dumps(key, pickle.HIGHEST_PROTOCOL)
        result = self.store.get(key)
        # B301:pickle key is set by developers and safe to pickle
        return None if result is None else pickle.loads(result)  # nosec B301

    def __setitem__(self, key, value, expire=None):
        key = pickle.dumps(key, pickle.HIGHEST_PROTOCOL)
        value = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
        if expire and expire <= 0:
            expire = None
        self.store.set(key, value, ex=expire)

    def __len__(self):
        self.size = self.store.dbsize()
        return self.size

    def __iter__(self):
        for key in self.store.scan_iter():
            try:
                # B301:pickle key is set by developers and safe to pickle
                yield pickle.loads(key)  # nosec B301
            except pickle.UnpicklingError:
                # If redis already has keys created by other apps, yield them as-is
                yield key

    @property
    def currsize(self):
        '''The current size of cache in bytes'''
        return self.store.info('memory').get('used_memory', None)

    @property
    def maxsize(self):
        '''The max size of cache in bytes'''
        return self.store.info('memory').get('maxmemory', None)

    def get(self, key, *args, **kwargs):
        return self.__getitem__(key)

    def set(self, key, value, expire=None):
        return self.__setitem__(key, value, expire)

    def keys(self):
        return self.store.keys()

    def flush(self):
        '''Delete all keys in the current database'''
        self.store.execute_command('FLUSHDB')
