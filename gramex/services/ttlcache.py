'''
Same as cachetools/ttl.py 3.0.0, but with option to specify an expiry for EACH key.
'''
# Modifications are marked with CHANGE:

from __future__ import absolute_import

import collections
import time

# CHANGE: import from cachetools instead of .cache
from cachetools import Cache

# CHANGE: MAXTTL is the default TTL = 10 years
MAXTTL = 86400 * 365 * 10       # noqa: ignore well known magic constants


class _Link(object):

    __slots__ = ('key', 'expire', 'next', 'prev')

    def __init__(self, key=None, expire=None):
        self.key = key
        self.expire = expire

    def __reduce__(self):
        return _Link, (self.key, self.expire)

    def unlink(self):
        next = self.next
        prev = self.prev
        prev.next = next
        next.prev = prev


class _Timer(object):

    def __init__(self, timer):
        self.__timer = timer
        self.__nesting = 0

    def __call__(self):
        if self.__nesting == 0:
            return self.__timer()
        else:
            return self.__time

    def __enter__(self):
        if self.__nesting == 0:
            self.__time = time = self.__timer()
        else:
            time = self.__time
        self.__nesting += 1
        return time

    def __exit__(self, *exc):
        self.__nesting -= 1

    def __reduce__(self):
        return _Timer, (self.__timer,)

    def __getattr__(self, name):
        return getattr(self.__timer, name)


class TTLCache(Cache):
    """LRU Cache implementation with per-item time-to-live (TTL) value."""

    # CHANGE: ttl parameter defaults to MAXTTL
    def __init__(self, maxsize, ttl=MAXTTL, timer=time.time, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__root = root = _Link()
        root.prev = root.next = root
        self.__links = collections.OrderedDict()
        self.__timer = _Timer(timer)
        self.__ttl = ttl
        # CHANGE: .set() is the same as setitem
        self.set = self.__setitem__

    def __contains__(self, key):
        try:
            link = self.__links[key]  # no reordering
        except KeyError:
            return False
        else:
            return not (link.expire < self.__timer())

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        try:
            link = self.__getlink(key)
        except KeyError:
            expired = False
        else:
            expired = link.expire < self.__timer()
        if expired:
            return self.__missing__(key)
        else:
            return cache_getitem(self, key)

    # CHANGE: optional expire=None parameter added
    def __setitem__(self, key, value, expire=None, cache_setitem=Cache.__setitem__):
        with self.__timer as time:
            self.expire(time)
            cache_setitem(self, key, value)
        try:
            link = self.__getlink(key)
        except KeyError:
            self.__links[key] = link = _Link(key)
        else:
            link.unlink()
        # CHANGE: Expire time based on expire parameter, or default TTL
        link.expire = time + (self.__ttl if expire is None else expire)
        link.next = root = self.__root
        link.prev = prev = root.prev
        prev.next = root.prev = link

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        link = self.__links.pop(key)
        link.unlink()
        if link.expire < self.__timer():
            raise KeyError(key)

    def __iter__(self):
        root = self.__root
        curr = root.next
        while curr is not root:
            # "freeze" time for iterator access
            with self.__timer as time:
                if not (curr.expire < time):
                    yield curr.key
            curr = curr.next

    def __len__(self):
        root = self.__root
        curr = root.next
        time = self.__timer()
        count = len(self.__links)
        while curr is not root and curr.expire < time:
            count -= 1
            curr = curr.next
        return count

    def __setstate__(self, state):
        self.__dict__.update(state)
        root = self.__root
        root.prev = root.next = root
        for link in sorted(self.__links.values(), key=lambda obj: obj.expire):
            link.next = root
            link.prev = prev = root.prev
            prev.next = root.prev = link
        self.expire(self.__timer())

    def __repr__(self, cache_repr=Cache.__repr__):
        with self.__timer as time:
            self.expire(time)
            return cache_repr(self)

    @property
    def currsize(self):
        with self.__timer as time:
            self.expire(time)
            return super(TTLCache, self).currsize

    @property
    def timer(self):
        """The timer function used by the cache."""
        return self.__timer

    @property
    def ttl(self):
        """The time-to-live value of the cache's items."""
        return self.__ttl

    def expire(self, time=None):
        """Remove expired items from the cache."""
        if time is None:
            time = self.__timer()
        root = self.__root
        curr = root.next
        links = self.__links
        cache_delitem = Cache.__delitem__
        while curr is not root and curr.expire < time:
            cache_delitem(self, curr.key)
            del links[curr.key]
            next = curr.next
            curr.unlink()
            curr = next

    def clear(self):
        with self.__timer as time:
            self.expire(time)
            Cache.clear(self)

    def get(self, *args, **kwargs):
        with self.__timer:
            return Cache.get(self, *args, **kwargs)

    def pop(self, *args, **kwargs):
        with self.__timer:
            return Cache.pop(self, *args, **kwargs)

    def setdefault(self, *args, **kwargs):
        with self.__timer:
            return Cache.setdefault(self, *args, **kwargs)

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used that
        has not already expired.

        """
        with self.__timer as time:
            self.expire(time)
            try:
                key = next(iter(self.__links))
            except StopIteration:
                raise KeyError(f'{self.__class__.__name__} is empty')
            else:
                return (key, self.pop(key))

    if hasattr(collections.OrderedDict, 'move_to_end'):
        def __getlink(self, key):       # noqa: ignore N802: function name should be in lowercase
            value = self.__links[key]
            self.__links.move_to_end(key)
            return value
    else:
        def __getlink(self, key):       # noqa: ignore N802: function name should be in lowercase
            value = self.__links.pop(key)
            self.__links[key] = value
            return value
