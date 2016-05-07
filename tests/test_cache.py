import os
import unittest
import gramex.config
import gramex.services
from . import server
from orderedattrdict import AttrDict
from .test_handlers import TestGramex
from gramex.services.urlcache import ignore_headers, MemoryCache, DiskCache

info = AttrDict()
HTTP_OK = 200


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
        self.assertIsInstance(cache['memory'], MemoryCache)
        cache_size = 20
        self.assertEqual(cache['memory-20'].maxsize, cache_size)

    def test_memory_cache_expiry(self):
        memory_cache = gramex.services.info.cache['memory-20']
        memory_cache.set('persistent', 'value', 10)
        memory_cache.set('transient', 'value', -1)
        self.assertEqual(memory_cache.get('persistent'), 'value')
        self.assertEqual(memory_cache.get('transient'), None)

    def test_disk_cache(self):
        cache = gramex.services.info.cache
        self.assertIsInstance(cache['disk'], DiskCache)
        self.assertEqual(cache['disk']._dir, info.folder + '/.cache-url')


class TestCacheBehaviour(TestGramex):
    'Test Gramex handler caching behaviour'
    @staticmethod
    def headers(r):
        return {name: r.headers[name] for name in r.headers if name not in ignore_headers}

    def eq(self, r1, r2):
        self.assertTrue(r1.status_code == r2.status_code == HTTP_OK)
        self.assertDictEqual(self.headers(r1), self.headers(r2))
        self.assertEqual(r1.text, r2.text)

    def ne(self, r1, r2):
        self.assertTrue(r1.status_code == r2.status_code == HTTP_OK)
        self.assertNotEqual(r1.text, r2.text)

    def test_cache_key(self):
        r1 = self.get('/cache/randomchar-nocache')
        self.ne(r1, self.get('/cache/randomchar-nocache'))

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
