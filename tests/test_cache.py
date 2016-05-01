import os
import unittest
import diskcache
import cachetools
import gramex.services
from orderedattrdict import AttrDict

info = AttrDict()


def setUpModule():
    # Test gramex.services.cache() as a pure function
    info.folder = os.path.dirname(os.path.abspath(__file__))
    info.config = gramex.config.PathConfig(os.path.join(info.folder, 'gramex.yaml'))
    gramex.services.cache(info.config.cache)


class TestCacheConstructor(unittest.TestCase):
    'Test gramex.services.cache() as a pure function'

    def test_memory_cache(self):
        cache = gramex.services.info.cache
        self.assertIsInstance(cache['memory'], cachetools.LRUCache)
        self.assertIsInstance(cache['memory-lru'], cachetools.LRUCache)
        self.assertIsInstance(cache['memory-lfu'], cachetools.LFUCache)

        self.assertNotIn('memory-nonexistent', cache)

        self.assertIsInstance(cache['memory-lru-20'], cachetools.LRUCache)
        self.assertEqual(cache['memory-lru-20'].maxsize, 20)

    def test_disk_cache(self):
        cache = gramex.services.info.cache
        self.assertIsInstance(cache['disk'], diskcache.Cache)
        self.assertEqual(cache['disk']._dir, info.folder + '/.cache-url')
