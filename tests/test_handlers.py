from . import TestGramex


redirect_codes = (301, 302)


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
