# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import TestGramex


class TestFunctionHandler(TestGramex):
    def test_args(self):
        etag = {'headers': {'Etag': True}}
        text = '{"args": [0, 1], "kwargs": {"a": "a", "b": "b"}}'
        self.check('/func/args', text=text, **etag)
        self.check('/func/args-split', text=text, **etag)

        text = '{"args": ["abc", 1], "kwargs": {"a": "abc", "b": 1}}'
        self.check('/func/args-variable', text=text, **etag)

        self.check('/func/handler', text='{"args": ["Handler"], "kwargs": {}', **etag)
        self.check('/func/handler-null', text='{"args": [], "kwargs": {}', **etag)
        self.check('/func/composite',
                   text='{"args": [0, "Handler"], "kwargs": {"a": "a", "handler": "Handler"}}',
                   **etag)

        text = '{"args": [0, "Handler"], "kwargs": {"a": {"b": 1}, "handler": "Handler"}}'
        self.check('/func/compositenested', text=text, **etag)
        self.check('/func/compositenested-split', text=text, **etag)
        self.check('/func/compositenested-variable', text=text, **etag)

        self.check('/func/dumpx?x=1&x=2', text='{"args": [["1", "2"]], "kwargs": {}}', **etag)

    def test_async(self):
        etag = {'headers': {'Etag': True}}
        text = '{"args": [0, 1], "kwargs": {"a": "a", "b": "b"}}'
        self.check('/func/async/args', text=text, **etag)
        self.check('/func/async/args-split', text=text, **etag)
        self.check('/func/async/http', text='{"args": [["1", "2"]], "kwargs": {}}', **etag)
        self.check('/func/async/http2',
                   text='{"args": [["1"]], "kwargs": {}}{"args": [["2"]], "kwargs": {}}', **etag)
        self.check('/func/async/calc',
                   text='[[250,250,250],[250,250,250],[250,250,250],[250,250,250]]', **etag)

    def test_json(self):
        self.check('/func/numpytypes')

    def test_iterator(self):
        no_etag = {'headers': {'Etag': False}}
        self.check('/func/iterator?x=1&x=2&x=3', text='123', **no_etag)
        self.check('/func/iterator/async?x=1&x=2&x=3', text='123', **no_etag)

    def test_redirect(self):
        r = self.get('/func/redirect', allow_redirects=False)
        self.assertEqual(r.headers.get('Location'), '/dir/index/')
        self.assertEqual(r.headers.get('Increment'), '1')

        r = self.get('/func/redirect?next=/abc', allow_redirects=False)
        self.assertEqual(r.headers.get('Location'), '/abc')
        self.assertEqual(r.headers.get('Increment'), '2')

        r = self.get('/func/redirect', headers={'NEXT': '/abc'}, allow_redirects=False)
        self.assertEqual(r.headers.get('Location'), '/abc')
        self.assertEqual(r.headers.get('Increment'), '3')

        r = self.get('/func/redirect?next=/def', headers={'NEXT': '/abc'}, allow_redirects=False)
        self.assertEqual(r.headers.get('Location'), '/def')
        self.assertEqual(r.headers.get('Increment'), '4')

    def test_path_args(self):
        self.check('/func/path_args/高/兴', text='["\\u9ad8", "\\u5174"]')

    def test_methods(self):
        self.check('/func/methods', method='get', code=405)
        self.check('/func/methods', method='delete', code=405)
        self.check('/func/methods', method='post')
        self.check('/func/methods', method='put')
