from __future__ import unicode_literals

import os
import pathlib
import unittest
import gramex.config
import gramex.services
from orderedattrdict import AttrDict
from . import TestGramex, tempfiles
from gramex.services.urlcache import ignore_headers, MemoryCache, DiskCache

OK, NOT_FOUND = 200, 404
info = AttrDict()


def setUpModule():
    # Test gramex.services.cache() as a pure function
    info.folder = os.path.dirname(os.path.abspath(__file__))
    info.config = gramex.config.PathConfig(os.path.join(info.folder, 'gramex.yaml'))
    gramex.services.cache(info.config.cache)


class TestCacheConstructor(unittest.TestCase):
    'Test gramex.services.cache() as a pure function'

    def check_cache_expiry(self, cache):
        cache.set('persistent', 'value', 10)
        cache.set('transient', 'value', -1)
        self.assertEqual(cache.get('persistent'), 'value')
        self.assertEqual(cache.get('transient'), None)

    def test_memory_cache(self):
        cache = gramex.services.info.cache
        self.assertIsInstance(cache['memory'], MemoryCache)
        cache_size = 20
        self.assertEqual(cache['memory-20'].maxsize, cache_size)
        self.check_cache_expiry(cache['memory-20'])

    def test_disk_cache(self):
        cache = gramex.services.info.cache
        self.assertIsInstance(cache['disk'], DiskCache)
        self.assertEqual(cache['disk']._dir, info.folder + '/.cache-url')
        self.check_cache_expiry(cache['disk'])


class TestCacheFunctionHandler(TestGramex):
    'Test Gramex handler caching behaviour'
    @staticmethod
    def headers(r):
        return {name: r.headers[name] for name in r.headers if name not in ignore_headers}

    def eq(self, r1, r2):
        self.assertTrue(r1.status_code == r2.status_code == OK)
        self.assertDictEqual(self.headers(r1), self.headers(r2))
        self.assertEqual(r1.text, r2.text)

    def ne(self, r1, r2):
        self.assertTrue(r1.status_code == r2.status_code == OK)
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


class TestCacheFileHandler(TestGramex):
    try:
        filename = u'.cache-file\u2013unicode.txt'
        pathlib.Path(filename)
    except UnicodeError:
        filename = '.cache-file.txt'
    content = u'\u2013'

    def test_cache(self):
        cache_file = os.path.join(info.folder, 'dir', self.filename)

        def check_value(content):
            r = self.get(u'/cache/filehandler/%s' % self.filename)
            self.assertEqual(r.status_code, OK)
            self.assertEqual(r.content, content)

        # # Delete the file. The initial response should be a 404
        if os.path.exists(cache_file):
            os.unlink(cache_file)
        r = self.get(u'/cache/filehandler/%s' % self.filename)
        self.assertEqual(r.status_code, NOT_FOUND)

        # Create the file. The response should be what we write
        with open(cache_file, 'wb') as handle:
            handle.write(self.content.encode('utf-8'))
        tempfiles.cache_file = self.filename
        check_value(self.content.encode('utf-8'))

        # Modify the file. The response should be what it was originally.
        with open(cache_file, 'wb') as handle:
            handle.write((self.content + self.content).encode('utf-8'))
        check_value(self.content.encode('utf-8'))

        # Delete the file. The response should be what it was.
        if os.path.exists(cache_file):
            os.unlink(cache_file)
        check_value(self.content.encode('utf-8'))

    def test_error_cache(self):
        cache_file = os.path.join(info.folder, 'dir', self.filename)

        if os.path.exists(cache_file):
            os.unlink(cache_file)
        r = self.get(u'/cache/filehandler-error/%s' % self.filename)
        self.assertEqual(r.status_code, NOT_FOUND)

        # Create the file. The response should be cached as 404
        with open(cache_file, 'wb') as handle:
            handle.write(self.content.encode('utf-8'))
        r = self.get(u'/cache/filehandler-error/%s' % self.filename)
        self.assertEqual(r.status_code, NOT_FOUND)
