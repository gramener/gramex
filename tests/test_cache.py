import os
import sys
import shlex
import pathlib
import requests
import unittest
import gramex.cache
import gramex.config
import gramex.services
from threading import Lock
from urllib.parse import urlencode
from redis import StrictRedis
from nose.tools import eq_, ok_
from nose.plugins.skip import SkipTest
from orderedattrdict import AttrDict
from . import TestGramex, tempfiles, folder
from gramex.http import OK, NOT_FOUND, NOT_MODIFIED
from gramex.services.urlcache import ignore_headers, MemoryCache, DiskCache, RedisCache

info = AttrDict()


def setUpModule():
    # Test gramex.services.cache() as a pure function
    info.folder = os.path.dirname(os.path.abspath(__file__))
    info.config = gramex.config.PathConfig(os.path.join(info.folder, 'gramex.yaml'))
    gramex.services.cache(info.config.cache)


class TestCacheConstructor(unittest.TestCase):
    # Test gramex.services.cache() as a pure function

    def check_cache_expiry(self, cache):
        cache.set('persistent', 'value', 10)
        cache.set('transient', 'value', -1)
        eq_(cache.get('persistent'), 'value')
        eq_(cache.get('transient'), None)

    def test_memory_cache(self):
        cache = gramex.services.info.cache
        self.assertIsInstance(cache['memory'], MemoryCache)
        cache_size = 1000
        eq_(cache['memory-small'].maxsize, cache_size)
        self.check_cache_expiry(cache['memory-small'])

    def test_memory_cache_size(self):
        memcache = gramex.services.info.cache['memory']
        old_keys = set(memcache.keys())
        data = gramex.cache.open(os.path.join(folder, 'sales.xlsx'))
        new_keys = set(memcache.keys()) - old_keys
        eq_(len(new_keys), 1)           # only 1 new key should have been added
        value = memcache[list(new_keys)[0]]
        ok_(gramex.cache.sizeof(value) > sys.getsizeof(data))

    def test_disk_cache(self):
        cache = gramex.services.info.cache
        self.assertIsInstance(cache['disk'], DiskCache)
        eq_(cache['disk']._directory, info.folder + '/.cache-url')
        self.check_cache_expiry(cache['disk'])

    def test_default_cache(self):
        # The memory: cache is set as the default cache.
        # Confirm that this is used by gramex.cache.open
        cache = gramex.services.info.cache['memory']
        path = os.path.join(info.folder, 'gramex.yaml')
        # When a file is opened with a clear cache, ...
        cache.clear()
        gramex.cache.open(path)
        keys = list(cache.keys())
        eq_(len(keys), 1)           # it has only 1 key
        eq_(keys[0][0], path)       # with the file we just opened

    def test_redis_cache(self):
        # Need to run a redis-server on localhost:6379:0
        if 'redis' not in gramex.services.info.cache:
            raise SkipTest('Redis Cache not created')
        cache = gramex.services.info.cache['redis']
        try:
            cache.store.ping()
        except Exception:
            raise SkipTest('Redis not set up at localhost')

        self.assertIsInstance(cache, RedisCache)
        # When YAML has size: 0, .maxsize is None on Windows/Old Redis, 0 on Linux/New Redis
        ok_(cache.maxsize in (0, None))

        cache.store.flushall()
        gramex.cache.open(os.path.join(folder, 'sales.xlsx'), _cache=cache)
        eq_(len(cache), 1)      # only 1 new key should have been added

        def lock(x):
            return Lock()       # Non Picklable object

        cache.store.flushall()
        gramex.cache.open(os.path.join(folder, 'sales.xlsx'), transform=lock, _cache=cache)
        eq_(len(cache), 0)  # It should not be cached

        r = StrictRedis()                   # Connect to redis without gramex cache
        r.set('Unpickled', 'Test')          # Set a key that is not pickled
        ok_(list(cache))                    # the unpicked key should not raise an Exception


class TestCacheKey(unittest.TestCase):
    # Test Gramex cache: key behaviour

    def test_request(self):
        def request(val):
            return AttrDict(request=AttrDict(val))

        # Check if request.* renders value as string
        cache_key = gramex.services._get_cache_key({'key': ['request.abc']}, 'request')
        eq_(cache_key(request({'x': 1})), '~')
        eq_(cache_key(request({'abc': None})), 'None')
        eq_(cache_key(request({'abc': 'λ–►'})), 'λ–►')
        # Just ensure that this produces different results. Exact serialisation is irrelevant
        self.assertNotEqual(cache_key(request({'abc': {'x': 1}})),
                            cache_key(request({'abc': {'x': 2}})))

    def test_user(self):
        def user(val):
            return AttrDict(request=AttrDict(uri='uri'), current_user=val)

        # Check if user.* works
        cache_key = gramex.services._get_cache_key({'key': ['request.uri', 'user.attr']}, 'user')
        eq_(cache_key(user(None)), ('uri', '~'))
        eq_(cache_key(user({})), ('uri', '~'))
        eq_(cache_key(user({'attr': 'λ–►'})), ('uri', 'λ–►'))
        eq_(cache_key(user({'attr': {'x': 1}}))[0], 'uri')
        eq_(cache_key(user({'attr': eq_}))[0], 'uri')

    def test_cookie(self):
        def cookie(key, value):
            return AttrDict(request=AttrDict(uri='uri', cookies={key: AttrDict(value=value)}))

        # Check if cookies.* works
        cache_key = gramex.services._get_cache_key(
            {'key': ['request.uri', 'cookies.sid2']}, 'cookie')
        eq_(cache_key(cookie('x', 1)), ('uri', '~'))
        eq_(cache_key(cookie('sid2', '')), ('uri', ''))
        eq_(cache_key(cookie('sid2', 'λ–►')), ('uri', 'λ–►'))

    def test_header(self):
        def header(key, value):
            return AttrDict(request=AttrDict(uri='uri', headers={key: value}))

        # Check if headers.* works
        cache_key = gramex.services._get_cache_key(
            {'key': ['request.uri', 'headers.key']}, 'headers')
        eq_(cache_key(header('x', 1)), ('uri', '~'))
        eq_(cache_key(header('key', '')), ('uri', ''))
        eq_(cache_key(header('key', 'λ–►')), ('uri', 'λ–►'))

    def test_arg(self):
        def arg(key, *values):
            # Mimic a handler object with .request.uri=... and .args=...
            return AttrDict(request=AttrDict(uri='uri'), args=AttrDict({key: values}))

        # Check if args.* works
        cache_key = gramex.services._get_cache_key({'key': ['request.uri', 'args.key']}, 'args')
        eq_(cache_key(arg('x', 'x')), ('uri', '~'))
        eq_(cache_key(arg('key', '')), ('uri', ''))
        eq_(cache_key(arg('key', 'a')), ('uri', 'a'))
        eq_(cache_key(arg('key', 'a', 'b')), ('uri', 'a, b'))


class TestCacheFunctionHandler(TestGramex):
    # Test Gramex handler caching behaviour
    @staticmethod
    def headers(r):
        return {name: r.headers[name] for name in r.headers if name not in ignore_headers}

    def eq(self, r1, r2):
        self.assertTrue(r1.status_code == r2.status_code == OK)
        self.assertDictEqual(self.headers(r1), self.headers(r2))
        eq_(r1.text, r2.text)

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

    def test_304_cache(self):
        # Make a request and note the number of times the request was called
        session = requests.Session()
        r1 = self.get('/cache/increment', session=session)
        incr = gramex.services.info.increment
        # Call a NEW URL with the Etag. It should return a 304 after recomputing.
        r2 = self.get('/cache/increment2', headers={'If-None-Match': r1.headers['Etag']})
        eq_(r2.status_code, NOT_MODIFIED)
        incr += 1
        eq_(incr, gramex.services.info.increment)
        # Call the same URL. The result should've been cached by now. Variable shouldn't increment.
        r3 = self.get('/cache/increment2', headers={'If-None-Match': r1.headers['Etag']})
        eq_(r3.status_code, NOT_MODIFIED)
        eq_(incr, gramex.services.info.increment)

    def test_multi_browser(self):
        # When a 304 is served as the first response, ensure original headers are not lost.
        session1 = requests.Session()
        # Request a dummy page to get the ETag
        r1 = self.get('/cache/increment-headers-dummy', session=session1)
        # Scenario: Browser 1 had a cached copy. But Gramex restarted.
        # So now it requests the page again.
        r2 = self.get('/cache/increment-headers', session=session1,
                      headers={'If-None-Match': r1.headers['Etag']})
        eq_(r2.status_code, NOT_MODIFIED)
        # Now, the server has re-cached the response. Since the response was a
        # 304 without headers, check that the server actually cached the original
        # headers, and not the empty headers returned by a 304 response.
        session2 = requests.Session()
        r3 = self.get('/cache/increment-headers', session=session2)
        eq_(r3.status_code, OK)
        eq_(r3.headers['Content-Type'], 'text/plain')


class TestCacheFileHandler(TestGramex):
    @classmethod
    def setUpClass(cls):
        try:
            cls.filename = '.cache-file\u2013unicode.txt'
            pathlib.Path(cls.filename)
        except UnicodeError:
            cls.filename = '.cache-file.txt'
        cls.content = '\u2013'
        cls.cache_file = os.path.join(info.folder, 'dir', cls.filename)

    def test_cache(self):

        def check_value(content):
            r = self.get(f'/cache/filehandler/{self.filename}')
            eq_(r.status_code, OK)
            eq_(r.content, content)

        # # Delete the file. The initial response should be a 404
        if os.path.exists(self.cache_file):
            os.unlink(self.cache_file)
        r = self.get('/cache/filehandler/%s' % self.filename)
        eq_(r.status_code, NOT_FOUND)

        # Create the file. The response should be what we write
        with open(self.cache_file, 'wb') as handle:
            handle.write(self.content.encode('utf-8'))
        tempfiles.cache_file = self.filename
        check_value(self.content.encode('utf-8'))

        # Modify the file. The response should be what it was originally.
        with open(self.cache_file, 'wb') as handle:
            handle.write((self.content + self.content).encode('utf-8'))
        check_value(self.content.encode('utf-8'))

        # Delete the file. The response should be what it was.
        if os.path.exists(self.cache_file):
            os.unlink(self.cache_file)
        check_value(self.content.encode('utf-8'))

    def test_error_cache(self):
        if os.path.exists(self.cache_file):
            os.unlink(self.cache_file)
        r = self.get('/cache/filehandler-error/%s' % self.filename)
        eq_(r.status_code, NOT_FOUND)

        # Create the file. The response should be cached as 404
        with open(self.cache_file, 'wb') as handle:
            handle.write(self.content.encode('utf-8'))
        r = self.get('/cache/filehandler-error/%s' % self.filename)
        eq_(r.status_code, NOT_FOUND)

    def test_binary_cache(self):
        self.check('/cache/filehandler/binary.bin')

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.cache_file):
            os.unlink(cls.cache_file)


class TestSubprocess(TestGramex):
    def test_subprocess(self):
        def proc(cmd, **kwargs):
            kwargs['args'] = shlex.split(cmd)
            return '/cache/subprocess?' + urlencode(kwargs, doseq=True)

        # Test that args runs commands
        self.check(proc('git log -n 1'), text='commit ')
        # Test that subprocess streams stdout & stderr. This runs 'python utils.py write_stream'
        # This writes o0, o1, o2 on stdout and e0, e1, e2 on stderr, interleaved
        cmd = 'python "%s" write_stream' % os.path.join(folder, 'utils.py')
        self.check(proc(cmd), text='stream: return: o0\no1\no2\ne0\ne1\ne2\n')
        self.check(proc(cmd, out=1, err=1, buf='line'), text='stream: o0\ne0\no1\ne1\no2\ne2\n')
        # Only one of stdout/stderr is streamed
        self.check(proc(cmd, out=1, buf='line'), text='stream: o0\no1\no2\nreturn: e0\ne1\ne2\n')
        self.check(proc(cmd, err=1, buf='line'), text='stream: e0\ne1\ne2\nreturn: o0\no1\no2\n')
        # Test that buffer_size is obeyed. We pick buf=6 because it will cover 2 rows - 'o0\no1\n'
        self.check(proc(cmd, out=1, err=1, buf=6), text='stream: o0\no1\ne0\ne1\n')
        # Test that kwargs is passed to subprocess.Popen()
        self.check(proc(cmd, env=1), text='GRAMEXTESTENV: test')

        # Test that streams accepts multiple fuctions that accept a bytestring
        self.check(proc(cmd, out=[1, 2], buf='line'), text='stream: o0\no0\no1\no1\no2\no2\n')
        self.check(proc(cmd, err=[1, 2], buf='line'), text='stream: e0\ne0\ne1\ne1\ne2\ne2\n')

        # If the process raises an Exception, ensure that it is raised
        # Ensure that this works with unicode
