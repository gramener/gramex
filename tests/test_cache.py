import io
import os
import unittest
import diskcache
import cachetools
import gramex.config
import gramex.services
from . import server
from orderedattrdict import AttrDict
from .test_handlers import TestGramex

info = AttrDict()


def setUpModule():
    # Test gramex.services.cache() as a pure function
    info.folder = os.path.dirname(os.path.abspath(__file__))
    info.config = gramex.config.PathConfig(os.path.join(info.folder, 'gramex.yaml'))
    gramex.services.cache(info.config.cache)

    # Set up the server for testing the cache
    server.start_gramex()


def tearDownModule():
    server.stop_gramex()


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


class TestCacheBehaviour(TestGramex):
    'Test Gramex handler caching behaviour'

    def eq(self, r1, r2):
        self.assertTrue(r1.status_code == r2.status_code == 200)
        self.assertEqual(r1.text, r2.text)

    def ne(self, r1, r2):
        self.assertTrue(r1.status_code == r2.status_code == 200)
        self.assertNotEqual(r1.text, r2.text)

    def test_cache_key(self):
        r1 = self.get('/cache/randomchar')
        self.eq(r1, self.get('/cache/randomchar'))
        self.ne(r1, self.get('/cache/randomchar?x=1'))

        r2 = self.get('/cache/pathkey')
        self.eq(r2, self.get('/cache/pathkey?key=value'))
        self.ne(r2, r1)

        r3 = self.get('/cache/host')
        self.eq(r3, self.get('/cache/host-new-path'))
        self.ne(r3, r1)

        r1 = self.get('/cache/args?x=1')
        r2 = self.get('/cache/args?x=1&y=2')
        self.eq(r1, r2)
        r3 = self.get('/cache/args?x=2&y=2')
        self.ne(r2, r3)

        r1 = self.get('/cache/header-test')
        r2 = self.get('/cache/header-test', headers={'Test': 'abc'})
        self.ne(r1, r2)

        r1 = self.get('/cache/cookie-test')
        r2 = self.get('/cache/cookie-test', cookies={'user': 'abc'})
        r3 = self.get('/cache/cookie-test', cookies={'user': 'def'})
        self.ne(r1, r2)
        self.ne(r2, r3)

        r1 = self.get('/cache/invalid-keys-ignored')
        r2 = self.get('/cache/invalid-keys-ignored-changed-url?x=1')
        self.ne(r1, r2)
