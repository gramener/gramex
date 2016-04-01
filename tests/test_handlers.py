import json
import requests
import markdown
import unittest
from orderedattrdict import AttrDict
from gramex.transforms import badgerfish
from . import server


setUpModule = server.start_gramex
tearDownModule = server.stop_gramex
redirect_codes = (301, 302)


class TestGramex(unittest.TestCase):
    'Base class to test Gramex running as a subprocess'

    def get(self, url, **kwargs):
        return requests.get(server.base_url + url, **kwargs)

    def check(self, url, path=None, code=200, text=None, headers=None):
        r = self.get(url)
        self.assertEqual(r.status_code, code, '%s: code %d != %d' % (url, r.status_code, code))
        if text is not None:
            self.assertIn(text, r.text, '%s: %s not in %s' % (url, text, r.text))
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


class TestFunctionHandler(TestGramex):
    'Test FunctionHandler'

    def test_args(self):
        'Test arguments'
        self.check('/func/args', text='{"args": [0, 1], "kwargs": {"a": "a", "b": "b"}}')
        self.check('/func/handler', text='{"args": ["Handler"], "kwargs": {}')
        self.check('/func/composite',
                   text='{"args": [0, "Handler"], "kwargs": {"a": "a", "handler": "Handler"}}')
        self.check('/func/compositenested',
                   text='{"args": [0, "Handler"], "kwargs": {"a": {"b": 1}, '
                        '"handler": "Handler"}}')
        self.check('/func/dumpx?x=1&x=2', text='{"args": [["1", "2"]], "kwargs": {}}')

    def test_async(self):
        self.check('/func/async_args', text='{"args": [0, 1], "kwargs": {"a": "a", "b": "b"}}')
        self.check('/func/async_http', text='{"args": [["1", "2"]], "kwargs": {}}')
        self.check('/func/async_http2',
                   text='{"args": [["1"]], "kwargs": {}}{"args": [["2"]], "kwargs": {}}')
        self.check('/func/async_calc',
                   text='[[250,250,250],[250,250,250],[250,250,250],[250,250,250]]')


class TestFileHandler(TestGramex):
    'Test FileHandler'

    def test_directoryhandler(self):
        'DirectoryHandler == FileHandler'
        from gramex.handlers import DirectoryHandler, FileHandler
        self.assertEqual(DirectoryHandler, FileHandler)

    def test_filehandler(self):
        'Test FileHandler'
        def adds_slash(url, check):
            self.assertFalse(url.endswith('/'), 'redirect_with_slash url must not end with /')
            r = self.get(url)
            if check:
                self.assertTrue(r.url.endswith('/'), url)
                self.assertIn(r.history[0].status_code, redirect_codes, url)
            else:
                self.assertEqual(len(r.history), 0)

        self.check('/dir/noindex/', code=404)
        adds_slash('/dir/noindex/subdir', False)
        self.check('/dir/noindex/subdir/', code=404)
        self.check('/dir/noindex/index.html', path='dir/index.html')
        self.check('/dir/noindex/text.txt', path='dir/text.txt')
        self.check('/dir/noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/index/', code=200, text='subdir/</a>')
        adds_slash('/dir/index/subdir', True)
        self.check('/dir/index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/index/index.html', path='dir/index.html')
        self.check('/dir/index/text.txt', path='dir/text.txt')
        self.check('/dir/index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-present-index/', path='dir/index.html')
        adds_slash('/dir/default-present-index/subdir', True)
        self.check('/dir/default-present-index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/default-present-index/index.html', path='dir/index.html')
        self.check('/dir/default-present-index/text.txt', path='dir/text.txt')
        self.check('/dir/default-present-index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-missing-index/', code=200, text='subdir/</a>')
        adds_slash('/dir/default-missing-index/subdir', True)
        self.check('/dir/default-missing-index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/default-missing-index/index.html', path='dir/index.html')
        self.check('/dir/default-missing-index/text.txt', path='dir/text.txt')
        self.check('/dir/default-missing-index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-present-noindex/', path='dir/index.html')
        adds_slash('/dir/default-present-noindex/subdir', False)
        self.check('/dir/default-present-noindex/subdir/', code=404)
        self.check('/dir/default-present-noindex/index.html', path='dir/index.html')
        self.check('/dir/default-present-noindex/text.txt', path='dir/text.txt')
        self.check('/dir/default-present-noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-missing-noindex/', code=404)
        adds_slash('/dir/default-missing-noindex/subdir', False)
        self.check('/dir/default-missing-noindex/subdir/', code=404)
        self.check('/dir/default-missing-noindex/index.html', path='dir/index.html')
        self.check('/dir/default-missing-noindex/text.txt', path='dir/text.txt')
        self.check('/dir/default-missing-noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/noindex/binary.bin', path='dir/binary.bin')

        self.check('/dir/args/?x=1', text=json.dumps({'x': ['1']}))
        self.check('/dir/args/?x=1&x=2&y=3', text=json.dumps({'x': ['1', '2'], 'y': ['3']},
                                                             sort_keys=True))

        self.check('/dir/data', code=200, path='dir/data.csv', headers={
            'Content-Type': 'text/plain',
            'Content-Disposition': None
        })

    def test_transforms(self):
        with (server.info.folder / 'dir/markdown.md').open(encoding='utf-8') as f:
            self.check('/dir/transform/markdown.md', text=markdown.markdown(f.read()))

        handler = AttrDict(file=server.info.folder / 'dir/badgerfish.yaml')
        with (server.info.folder / 'dir/badgerfish.yaml').open(encoding='utf-8') as f:
            result = yield badgerfish(f.read(), handler)
            self.check('/dir/transform/badgerfish.yaml', text=result)
            self.check('/dir/transform/badgerfish.yaml', text='imported file')
