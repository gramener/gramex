import os
import requests
from . import server
from . import TestGramex
from gramex.http import OK, NOT_FOUND, INTERNAL_SERVER_ERROR, FORBIDDEN


class TestURLPriority(TestGramex):
    # Test Gramex URL priority sequence

    def test_url_priority(self):
        self.check('/path/abc', text='/path/.*')
        self.check('/path/file', text='/path/file')
        self.check('/path/dir', text='/path/.*')
        self.check('/path/dir/', text='/path/dir/.*')
        self.check('/path/dir/abc', text='/path/dir/.*')
        self.check('/path/dir/file', text='/path/dir/file')
        self.check('/path/priority', text='/path/priority')


class TestURLNormalization(TestGramex):
    # Test URL pattern normalization

    def test_url_normalization(self):
        self.check('/path/norm1', text='/path/norm1')
        self.check('/path/norm2', text='/path/norm2')


class TestAttributes(TestGramex):
    # Ensure that BaseHandler subclasses have relevant attributes

    def test_attributes(self):
        self.check('/func/attributes', code=OK)


class TestXSRF(TestGramex):
    # Test BaseHandler xsrf: setting

    def test_xsrf(self):
        r = self.check('/path/norm')
        self.assertFalse('Set-Cookie' in r.headers)

        # First request sets xsrf cookie
        session = requests.Session()
        r = session.get(server.base_url + '/xsrf', timeout=10)
        self.assertTrue('Set-Cookie' in r.headers)
        self.assertTrue('_xsrf' in r.headers['Set-Cookie'])

        # Next request does not set xsrf cookie, because it already exists
        r = session.get(server.base_url + '/xsrf', timeout=10)
        self.assertFalse('Set-Cookie' in r.headers)

    def test_xsrf_false(self):
        # When xsrf_cookies is set to False, POST works
        r = requests.post(server.base_url + '/xsrf/no')
        self.assertEqual(r.status_code, OK)

    def test_xsrf_true(self):
        # When xsrf_cookies is set to True, POST fails without _xsrf
        r = requests.post(server.base_url + '/xsrf/yes')
        self.assertEqual(r.status_code, FORBIDDEN)

    def test_ajax(self):
        # Requests sent with X-Requested-With should not need an XSRF cookie
        r = requests.post(server.base_url + '/xsrf/yes', headers={
            # Mangle case below to ensure Gramex handles it case-insensitively
            'X-Requested-With': 'xMlHtTpReQuESt',
        })
        self.assertEqual(r.status_code, OK)


class TestErrorHandling(TestGramex):
    # Test BaseHandler error: setting
    def test_error(self):
        for code, url in ((NOT_FOUND, '/error/404-template-na'),
                          (INTERNAL_SERVER_ERROR, '/error/500-function')):
            r = self.check(url, code=code)
            self.assertEqual(r.headers['Content-Type'], 'application/json')
            result = r.json()
            self.assertEqual(result['status_code'], code)
            self.assertTrue(result['handler.request.uri'].endswith(url))


class TestMime(TestGramex):
    def setUp(self):
        self.mime_map = {
            '.yml': 'text/yaml; charset=UTF-8',
            '.yaml': 'text/yaml; charset=UTF-8',
            '.md': 'text/markdown; charset=UTF-8',
            '.markdown': 'text/markdown; charset=UTF-8',
            '.json': 'application/json',
            '.svg': 'image/svg+xml',
            # '.py': 'text/plain; charset=UTF-8',       # .py files are forbidden by default
            '.h5': 'application/x-hdf5',
            '.hdf5': 'application/x-hdf5',
        }
        self.files = set()
        folder = os.path.dirname(os.path.abspath(__file__))
        for ext, mime in self.mime_map.items():
            path = os.path.join(folder, 'dir', 'gen' + ext)
            self.files.add(path)
            with open(path, 'wb'):
                pass

    def test_mime(self):
        for ext, mime in self.mime_map.items():
            r = self.check('/dir/gen' + ext)
            self.assertEqual(r.headers['Content-Type'], mime)

    def tearDown(self):
        for file in self.files:
            os.unlink(file)


class TestBaseHandler(TestGramex):
    def test_headers(self):
        self.check('/', headers={'X-BaseHandler': 'base'})
