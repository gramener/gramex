import json

from . import TestGramex
from gramex.http import FOUND
from gramex.handlers.functionhandler import add_handler


@add_handler
def total(*items: float) -> float:
    return sum(items)


@add_handler
def strtotal(*items: str) -> str:
    s = ''
    for i in items:
        s += i
    return s


@add_handler
def name_age(name, age):
    return f'{name} is {age} years old.'


@add_handler
def urlparse_hinted(name: str, age: int) -> str:
    return f'{name} is {age} years old.'


@add_handler
def native_types(a: int, b: float, c: bool, d: None):
    return {'msg': f'{a} items @ {b} each together cost {a * b}.', 'c': c, 'd': d}


@add_handler
def greet(name="Stranger"):
    return f'Hello, {name}!'


class TestFunctionHandler(TestGramex):

    def test_add_handler_get(self):
        self.check('/func/total/40/2', text="42.0")
        self.check('/func/name/johndoe/age/42', text="johndoe is 42 years old.")
        self.check('/func/foo?name=johndoe&age=42', text="johndoe is 42 years old.")
        # When type hints are violated:
        self.check('/func/hints?name=johndoe&age=42.3', code=500)
        # When multiple arguments are passed:
        self.check('/func/multi?items=1&items=2&items=3', text="6.0")
        # Positional args with types
        self.check('/func/strtotal?items=a&items=b&items=c', text='abc')
        # Test native types:
        self.check(
            '/func/nativetypes?a=3&b=1.5&c=false&d=null',
            text='{"msg": "3 items @ 1.5 each together cost 4.5.", "c": false, "d": "null"}')
        self.check('/func/defaultNamed', text="Hello, Stranger!")
        self.check('/func/defaultNamed?name=gramex', text="Hello, gramex!")

    def test_add_handler_delete(self):
        self.check('/func/total/40/2', text="42.0", method='delete')

    def test_add_handler_post(self):
        self.check(
            '/func/foo', method='post', data={'name': 'johndoe', 'age': '42'},
            text="johndoe is 42 years old.")
        self.check(
            '/func/foo', method='post', data=json.dumps({'name': 'johndoe', 'age': '42'}),
            text="johndoe is 42 years old.")
        # When type hints are violated:
        self.check('/func/hints', method='post', data={'name': 'johndoe', 'age': '42.3'},
                   code=500)
        # When POSTing positional args
        self.check('/func/multi', method='post', data={'items': [1, 2, 3]}, code=500)
        # Check typecasting
        self.check(
            '/func/nativetypes', method='post',
            data=json.dumps({'a': 3, 'b': 1.5, 'c': False, 'd': None}),
            text='{"msg": "3 items @ 1.5 each together cost 4.5.", "c": false, "d": null}')
        self.check('/func/defaultNamed', text="Hello, Stranger!")

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
