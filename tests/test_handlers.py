import requests
import unittest
from . import server


setUpModule = server.start_gramex
tearDownModule = server.stop_gramex
redirect_codes = (301, 302)


class TestGramex(unittest.TestCase):
    'Base class to test Gramex running as a subprocess'

    def get(self, url, **kwargs):
        return requests.get(server.base_url + url, **kwargs)

    def check(self, url, path=None, code=200, text=None, no_text=None, headers=None):
        r = self.get(url)
        self.assertEqual(r.status_code, code, '%s: code %d != %d' % (url, r.status_code, code))
        if text is not None:
            self.assertIn(text, r.text, '%s: %s not in %s' % (url, text, r.text))
        if no_text is not None:
            self.assertNotIn(text, r.text, '%s: %s should not be in %s' % (url, text, r.text))
        if path is not None:
            with (server.info.folder / path).open('rb') as file:
                self.assertEqual(r.content, file.read(), '%s != %s' % (url, path))
        if headers is not None:
            for header, value in headers.items():
                if value is None:
                    self.assertFalse(header in r.headers,
                                     '%s: should not have header %s' % (url, header))
                else:
                    actual = r.headers[header]
                    self.assertEqual(actual, value,
                                     '%s: header %s = %s != %s' % (url, header, actual, value))
        return r


class TestURLPriority(TestGramex):
    'Test Gramex URL priority sequence'

    def test_url_priority(self):
        self.check('/path/abc', text='/path/.*')
        self.check('/path/file', text='/path/file')
        self.check('/path/dir', text='/path/.*')
        self.check('/path/dir/', text='/path/dir/.*')
        self.check('/path/dir/abc', text='/path/dir/.*')
        self.check('/path/dir/file', text='/path/dir/file')
        self.check('/path/priority', text='/path/priority')


class TestURLNormalization(TestGramex):
    'Test URL pattern normalization'

    def test_url_normalization(self):
        self.check('/path/norm1', text='/path/norm1')
        self.check('/path/norm2', text='/path/norm2')


class TestFunctionHandler(TestGramex):
    'Test FunctionHandler'

    def test_args(self):
        self.check('/func/args', text='{"args": [0, 1], "kwargs": {"a": "a", "b": "b"}}')
        self.check('/func/handler', text='{"args": ["Handler"], "kwargs": {}')
        self.check('/func/composite',
                   text='{"args": [0, "Handler"], "kwargs": {"a": "a", "handler": "Handler"}}')
        self.check('/func/compositenested',
                   text='{"args": [0, "Handler"], "kwargs": {"a": {"b": 1}, '
                        '"handler": "Handler"}}')
        self.check('/func/dumpx?x=1&x=2', text='{"args": [["1", "2"]], "kwargs": {}}')

    def test_async(self):
        self.check('/func/async/args', text='{"args": [0, 1], "kwargs": {"a": "a", "b": "b"}}')
        self.check('/func/async/http', text='{"args": [["1", "2"]], "kwargs": {}}')
        self.check('/func/async/http2',
                   text='{"args": [["1"]], "kwargs": {}}{"args": [["2"]], "kwargs": {}}')
        self.check('/func/async/calc',
                   text='[[250,250,250],[250,250,250],[250,250,250],[250,250,250]]')

    def test_iterator(self):
        self.check('/func/iterator?x=1&x=2&x=3', text='123')
        self.check('/func/iterator/async?x=1&x=2&x=3', text='123')
