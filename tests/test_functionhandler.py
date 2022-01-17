import json
import gramex.cache
import pandas as pd
from gramex.http import FOUND
from . import TestGramex, afe


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
        for method in ['post', 'put']:
            r = self.get('/func/methods', method=method,
                         headers={'NEXT': '/abc'}, allow_redirects=False)
            self.assertEqual(r.status_code, FOUND)
            self.assertEqual(r.headers.get('Location'), '/abc')


class TestWrapper(TestGramex):
    def test_config_kwargs(self):
        self.check('/func/power?y=3', text='9.0')
        self.check('/func/power?y=3&x=3', text='27.0')

    def test_yielder(self):
        self.check('/func/yielder?i=a&i=b&i=c', text='abc')

    def test_add_handler_get(self):
        self.check('/func/total/40/2', text='42.0')
        self.check('/func/total/40/2?items=10', text='52.0')
        self.check('/func/total/40/2?items=10&items=10', text='62.0')
        self.check('/func/name_age/johndoe/age/42', text='johndoe is 42 years old.')
        self.check('/func/name_age', text='alpha is 10 years old.')
        self.check('/func/name_age?name=johndoe&age=42', text='johndoe is 42 years old.')
        # In case of multiple kwargs, the last parameter is picked
        self.check('/func/name_age?name=x&name=y&age=1&age=2', text='y is 2 years old.')
        # When type hints are violated:
        self.check('/func/hints?name=johndoe&age=42.3', code=500)
        # When multiple arguments are passed:
        self.check('/func/total?items=1&items=2&items=3', text='6.0')
        self.check('/func/multilist?items=1&items=2&items=3&start=1', text='7.0')
        # Positional args with types
        self.check('/func/strtotal?items=a&items=b&items=c', text='abc')
        # Test native types. Note: "i=false" won't work -- use "i=" since it's a np.bool8
        # Note: datetimes must be quoted, since they'll be read as JSON usually.
        self.check(
            '/func/nativetypes?a=3&b=1.5&c=false&d=d&e=null&f=3&g=1.5&h=h&i=',
            text=''.join(['3', '1.5', 'false', 'd', '', '3', '1.5', 'h', 'false',
                          '"2020-01-01T00:00:00+00:00"', '{"a":3,"b":1.5}', '[3,1.5]']))
        self.check('/func/greet', text='Hello, Stranger!')
        self.check('/func/greet?name=gramex', text='Hello, gramex!')
        self.check('/func/multilist?items=1&items=2&items=3&start=1', text='7.0')
        sales = self.check('/func/sales').json()
        afe(pd.DataFrame(sales), gramex.cache.open('sales.xlsx', rel=True))
        self.check('/func/content/003.json',
                   text='{"x":3}',
                   headers={'Content-Type': 'application/json'})
        self.check('/func/content/003.txt',
                   text='x=3',
                   headers={'Content-Type': 'text/plain'})

    def test_add_handler_post(self):
        self.check(
            '/func/name_age', method='post', data={'name': 'johndoe', 'age': '42'},
            text='johndoe is 42 years old.')
        self.check(
            '/func/name_age', method='post', data=json.dumps({'name': 'johndoe', 'age': '42'}),
            request_headers={'Content-Type': 'application/json'},
            text='johndoe is 42 years old.')
        # When type hints are violated:
        self.check('/func/hints', method='post', data={'name': 'johndoe', 'age': '42.3'},
                   code=500)
        # Check typecasting
        self.check(
            '/func/nativetypes', method='post',
            data=json.dumps({'a': 3, 'b': 1.5, 'c': False, 'd': 'd', 'e': None, 'f': 3,
                             'g': 1.5, 'h': 'h', 'i': False}),
            request_headers={'Content-Type': 'application/json'},
            text=''.join(['3', '1.5', 'false', 'd', '', '3', '1.5', 'h', 'false',
                          '"2020-01-01T00:00:00+00:00"', '{"a":3,"b":1.5}', '[3,1.5]']))
        self.check('/func/greet', text='Hello, Stranger!')
        # Check if POSTing url params and path args works
        self.check('/func/name_age?name=johndoe&age=42', method='post',
                   text='johndoe is 42 years old.')
        self.check('/func/name_age/johndoe/age/42', text='johndoe is 42 years old.')

    def test_add_handler_delete(self):
        self.check('/func/total/40/2?items=10&items=20', text='72.0', method='delete')
