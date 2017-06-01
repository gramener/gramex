from . import TestGramex


class TestFunctionHandler(TestGramex):
    'Test FunctionHandler'

    def test_args(self):
        etag = {'headers': {'Etag': True}}
        self.check('/func/args', text='{"args": [0, 1], "kwargs": {"a": "a", "b": "b"}}', **etag)
        self.check('/func/handler', text='{"args": ["Handler"], "kwargs": {}', **etag)
        self.check('/func/composite',
                   text='{"args": [0, "Handler"], "kwargs": {"a": "a", "handler": "Handler"}}',
                   **etag)
        self.check('/func/compositenested',
                   text='{"args": [0, "Handler"], "kwargs": {"a": {"b": 1}, '
                        '"handler": "Handler"}}', **etag)
        self.check('/func/dumpx?x=1&x=2', text='{"args": [["1", "2"]], "kwargs": {}}', **etag)

    def test_async(self):
        etag = {'headers': {'Etag': True}}
        self.check('/func/async/args', text='{"args": [0, 1], "kwargs": {"a": "a", "b": "b"}}',
                   **etag)
        self.check('/func/async/http', text='{"args": [["1", "2"]], "kwargs": {}}', **etag)
        self.check('/func/async/http2',
                   text='{"args": [["1"]], "kwargs": {}}{"args": [["2"]], "kwargs": {}}', **etag)
        self.check('/func/async/calc',
                   text='[[250,250,250],[250,250,250],[250,250,250],[250,250,250]]', **etag)

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
