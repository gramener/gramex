import six
from six.moves import cPickle
from redis import StrictRedis


class RedisCache():
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
    and not specific to a db.

    Both Keys and Values are stored as pickle dump.
    This is an approximate LRU implementaion. Read more here.(https://redis.io/topics/lru-cache)
    '''
    def __init__(self, path=None, maxsize=None, *args, **kwargs):
        host, port, db, redis_kwargs = 'localhost', 6379, 0, {}
        if isinstance(path, six.string_types):
            parts = path.split(':')
            if len(parts):
                host = parts.pop(0)
            if len(parts):
                port = int(parts.pop(0))
            if len(parts):
                db = int(parts.pop(0))
            redis_kwargs = dict(part.split('=', 2) for part in parts)
        redis_kwargs['decode_responses'] = False
        r = StrictRedis(host=host, port=port, db=db, **redis_kwargs)
        self.store = r
        self.size = 0
        if maxsize is not None:
            if self.currsize > maxsize:
                self.flush()
            self.store.config_set('maxmemory', maxsize)
            self.store.config_set('maxmemory-policy', 'allkeys-lru')  # Approximate LRU cache

    def __getitem__(self, key):
        key = cPickle.dumps(key, cPickle.HIGHEST_PROTOCOL)
        result = self.store.get(key)
        return None if result is None else cPickle.loads(result)

    def __setitem__(self, key, value, expire=None):
        key = cPickle.dumps(key, cPickle.HIGHEST_PROTOCOL)
        value = cPickle.dumps(value, cPickle.HIGHEST_PROTOCOL)
        if expire and expire <= 0:
            expire = None
        self.store.set(key, value, ex=expire)

    def __len__(self):
        self.size = self.store.dbsize()
        return self.size

    def __iter__(self):
        for key in self.store.scan_iter():
            yield cPickle.loads(key)

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
