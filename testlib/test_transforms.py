# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import io
import os
import six
import yaml
import inspect
import unittest
from dis import dis
from types import GeneratorType
from tornado.gen import coroutine, Task
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from gramex.transforms import build_transform, flattener, badgerfish, template, once
from gramex.cache import reload_module
from nose.tools import eq_, assert_raises

folder = os.path.dirname(os.path.abspath(__file__))


def yaml_parse(text):
    return yaml.load(text, Loader=AttrDictYAMLLoader)


def remove(path):
    if os.path.exists(path):
        os.unlink(path)


@coroutine
def gen_str(val):
    '''Sample coroutine method'''
    yield Task(str, val)


def eqfn(actual, expected):
    '''Checks if two functions are the same'''
    # msg = parent function's name
    msg = inspect.stack()[1][3]
    a_code, e_code = actual.__code__, expected.__code__
    actual, expected = a_code.co_code, e_code.co_code
    if actual != expected:
        # Print the disassembled code to make debugging easier
        print('\nActual')           # noqa
        dis(actual)
        print(a_code.co_names)      # noqa
        print('Expected')           # noqa
        dis(expected)
        print(e_code.co_names)      # noqa
    eq_(actual, expected, '%s: code mismatch' % msg)

    src, tgt = a_code.co_argcount, e_code.co_argcount
    eq_(src, tgt, '%s: argcount %d != %d' % (msg, src, tgt))
    src, tgt = a_code.co_nlocals, e_code.co_nlocals
    eq_(src, tgt, '%s: nlocals %d != %d' % (msg, src, tgt))


class BuildTransform(unittest.TestCase):
    '''Test build_transform CODE output'''
    dummy = os.path.join(folder, 'dummy.py')
    files = set([dummy])

    def check_transform(self, transform, yaml_code, vars=None, cache=True, iter=True):
        fn = build_transform(yaml_parse(yaml_code), vars=vars, cache=cache, iter=iter)
        eqfn(fn, transform)
        return fn

    def test_invalid_function_raises_error(self):
        with assert_raises(KeyError):
            build_transform({})
        with assert_raises(KeyError):
            build_transform({'function': ''})
        with assert_raises(ValueError):
            build_transform({'function': 'x = 1'})
        with assert_raises(ValueError):
            build_transform({'function': 'x(); y()'})
        with assert_raises(ValueError):
            build_transform({'function': 'import json'})

    def test_expr(self):
        def transform(x=0):
            result = x + 1
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, 'function: x + 1', vars={'x': 0})

        def transform(x=0):
            result = x + 1
            return result
        self.check_transform(transform, 'function: x + 1', vars={'x': 0}, iter=False)

        def transform():
            result = "abc"
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''function: '"abc"' ''', vars={})

        def transform():
            import gramex.cache
            import pandas
            result = gramex.cache.open('x', pandas.read_csv).to_html()
            return result if isinstance(result, GeneratorType) else [result, ]
        fn = 'function: gramex.cache.open("x", pandas.read_csv).to_html()'
        self.check_transform(transform, fn, vars={})

        def transform(s=None):
            result = 1 if "windows" in s.lower() else 2 if "linux" in s.lower() else 0
            return result if isinstance(result, GeneratorType) else [result, ]
        fn = 'function: 1 if "windows" in s.lower() else 2 if "linux" in s.lower() else 0'
        self.check_transform(transform, fn, vars={'s': None})

        def transform(_val):
            result = condition(1, 0, -1)    # noqa: this is in gramex.transforms
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, 'function: condition(1, 0, -1)')

        def transform(_val):
            import six
            result = six.text_type.upper(_val)
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, 'function: six.text_type.upper')
        self.check_transform(transform, 'function: six.text_type.upper(_val)')

    def test_fn(self):
        def transform(_val):
            result = len(_val)
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''
            function: len
        ''')

    def test_fn_no_args(self):
        def transform():
            result = max(1, 2)
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''
            function: max
            args: [1, 2]
        ''', vars={})
        self.check_transform(transform, 'function: max(1, 2)', vars={})

    def test_fn_args(self):
        def transform(_val):
            result = max(1, 2)
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''
            function: max
            args: [1, 2]
        ''')
        self.check_transform(transform, 'function: max(1, 2)')

        def transform(_val):
            result = len('abc')
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''
            function: len
            args: abc
        ''')
        self.check_transform(transform, 'function: len("abc")')

        def transform(_val):
            result = range(10)
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''
            function: range
            args: 10
        ''')
        self.check_transform(transform, 'function: range(10)')

    def test_fn_args_var(self):
        def transform(x=1, y=2):
            result = max(x, y, 3)
            return result if isinstance(result, GeneratorType) else [result, ]
        vars = AttrDict([('x', 1), ('y', 2)])
        self.check_transform(transform, '''
            function: max
            args:
                - =x
                - =y
                - 3
        ''', vars=vars)
        self.check_transform(transform, 'function: max(x, y, 3)', vars=vars)

    def test_fn_kwargs(self):
        def transform(_val):
            result = dict(_val, a=1, b=2)
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''
            function: dict
            kwargs: {a: 1, b: 2}
        ''')
        self.check_transform(transform, 'function: dict(_val, a=1, b=2)')

    def test_fn_kwargs_complex(self):
        def transform(_val):
            result = dict(_val, a=[1, 2], b=AttrDict([('b1', 'x'), ('b2', 'y')]))
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''
            function: dict
            kwargs:
                a: [1, 2]
                b:
                    b1: x
                    b2: y
        ''')
        self.check_transform(transform, '''
            function: 'dict(_val, a=[1, 2], b=AttrDict([("b1", "x"), ("b2", "y")]))'
        ''')

    def test_fn_kwargs_var(self):
        def transform(x=1, y=2):
            result = dict(x, y, a=x, b=y, c=3, d='=4')
            return result if isinstance(result, GeneratorType) else [result, ]
        vars = AttrDict([('x', 1), ('y', 2)])
        self.check_transform(transform, '''
            function: dict
            kwargs: {a: =x, b: =y, c: 3, d: ==4}
        ''', vars=vars)
        self.check_transform(transform, 'function: dict(x, y, a=x, b=y, c=3, d="=4")', vars=vars)

    def test_fn_args_kwargs(self):
        def transform(_val):
            result = format(1, 2, a=3, b=4, c=5, d='=6')
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''
            function: format
            args: [1, 2]
            kwargs: {a: 3, b: 4, c: 5, d: ==6}
        ''')
        self.check_transform(transform, 'function: format(1, 2, a=3, b=4, c=5, d="=6")')

    def test_fn_args_kwargs_var(self):
        def transform(x=1, y=2):
            result = format(x, y, a=x, b=y, c=3)
            return result if isinstance(result, GeneratorType) else [result, ]
        vars = AttrDict([('x', 1), ('y', 2)])
        self.check_transform(transform, '''
            function: format
            args: [=x, =y]
            kwargs: {a: =x, b: =y, c: =3}
        ''', vars=vars)
        self.check_transform(transform, 'function: format(x, y, a=x, b=y, c=3)', vars=vars)

    def test_coroutine(self):
        def transform(_val):
            import testlib.test_transforms
            result = testlib.test_transforms.gen_str(_val)
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''
            function: testlib.test_transforms.gen_str
        ''')
        self.check_transform(transform, 'function: testlib.test_transforms.gen_str(_val)')

    def test_cache_change(self):
        remove(self.dummy.replace('.py', '.pyc'))
        with io.open(self.dummy, 'w', encoding='utf-8') as handle:
            handle.write('def value():\n\treturn 1\n')

        def transform(_val):
            import testlib.dummy
            reload_module(testlib.dummy)
            result = testlib.dummy.value()
            return result if isinstance(result, GeneratorType) else [result, ]

        fn = self.check_transform(transform, '''
            function: testlib.dummy.value
            args: []
        ''', cache=False)
        eq_(fn(), [1])
        fn = self.check_transform(transform, 'function: testlib.dummy.value()', cache=False)
        eq_(fn(), [1])

        remove(self.dummy.replace('.py', '.pyc'))
        with io.open(self.dummy, 'w', encoding='utf-8') as handle:
            handle.write('def value():\n\treturn 100\n')
        eq_(fn(), [100])
        fn = self.check_transform(transform, 'function: testlib.dummy.value()', cache=False)
        eq_(fn(), [100])

    def test_invalid_change(self):
        fn = build_transform(yaml_parse('function: testlib.dummy.invalid\nargs: []'))

        remove(self.dummy.replace('.py', '.pyc'))
        with io.open(self.dummy, 'w', encoding='utf-8') as handle:
            handle.write('def invalid():\n\tsyntax error\n')
        with assert_raises(SyntaxError):
            fn()

        remove(self.dummy.replace('.py', '.pyc'))
        with io.open(self.dummy, 'w', encoding='utf-8') as handle:
            handle.write('1/0\ndef invalid():\n\treturn 100\n')
        with assert_raises(ZeroDivisionError):
            fn()

        remove(self.dummy.replace('.py', '.pyc'))
        with io.open(self.dummy, 'w', encoding='utf-8') as handle:
            handle.write('def invalid():\n\treturn 100\n')
        eq_(fn(), [100])

    def test_import_levels(self):
        def transform(_val):
            import six
            result = six.text_type(_val)
            return result if isinstance(result, GeneratorType) else [result, ]
        fn = self.check_transform(transform, 'function: six.text_type')
        eq_(fn(b'abc'), [six.text_type(b'abc')])

        def transform(content):
            import six
            result = six.text_type.__add__(content, '123')
            return result if isinstance(result, GeneratorType) else [result, ]
        fn = self.check_transform(transform, '''
            function: six.text_type.__add__
            args: [=content, '123']
        ''', vars=AttrDict(content=None))
        eq_(fn('abc'), ['abc123'])

        def transform(handler):
            result = str.endswith(handler.current_user.user, 'ta')
            return result if isinstance(result, GeneratorType) else [result, ]
        fn = self.check_transform(transform, '''
            function: str.endswith
            args: [=handler.current_user.user, 'ta']
        ''', vars=AttrDict(handler=None))

    @classmethod
    def tearDownClass(cls):
        # Remove temporary files
        for path in cls.files:
            if os.path.exists(path):
                os.unlink(path)


class Badgerfish(unittest.TestCase):
    'Test gramex.transforms.badgerfish'

    def test_transform(self):
        result = yield badgerfish('''
        html:
          "@lang": en
          p: text
          div:
            p: text
        ''')
        eq_(
            result,
            '<!DOCTYPE html>\n<html lang="en"><p>text</p><div><p>text</p></div></html>')

    def test_mapping(self):
        result = yield badgerfish('''
        html:
          json:
            x: 1
            y: 2
        ''', mapping={
            'json': {
                'function': 'json.dumps',
                'kwargs': {'separators': [',', ':']},
            }
        })
        eq_(
            result,
            '<!DOCTYPE html>\n<html><json>{"x":1,"y":2}</json></html>')


class Template(unittest.TestCase):
    'Test gramex.transforms.template'
    def check(self, content, expected, **kwargs):
        result = yield template(content, **kwargs)
        eq_(result, expected)

    def test_template(self):
        self.check('{{ 1 }}', '1')
        self.check('{{ 1 + 2 }}', '3')
        self.check('{{ x + y }}', '3', x=1, y=2)


class Flattener(unittest.TestCase):
    def test_dict(self):
        fieldmap = {
            'all1': '',
            'all2': True,
            'x': 'x',
            'y.z': 'y.z',
            'z.1': 'z.1',
        }
        flat = flattener(fieldmap)
        src = {'x': 'X', 'y': {'z': 'Y.Z'}, 'z': ['Z.0', 'Z.1']}
        out = flat(src)
        eq_(out.keys(), fieldmap.keys())
        eq_(out['all1'], src)
        eq_(out['all2'], src)
        eq_(out['x'], src['x'])
        eq_(out['y.z'], src['y']['z'])
        eq_(out['z.1'], src['z'][1])

    def test_list(self):
        # Integer values must be interpreted as array indices
        fieldmap = {
            '0': 0,
            '1': '1',
            '2.0': '2.0',
        }
        flat = flattener(fieldmap)
        src = [0, 1, [2]]
        out = flat(src)
        eq_(out.keys(), fieldmap.keys())
        eq_(out['0'], src[0])
        eq_(out['1'], src[1])
        eq_(out['2.0'], src[2][0])

    def test_invalid(self):
        # None of these fields are valid. Don't raise an error, just ignore
        fieldmap = {
            0: 'int-invalid',
            ('a', 'b'): 'tuple-invalid',
            'false-invalid': False,
            'none-invalid': None,
            'float-invalid': 1.0,
            'dict-invalid': {},
            'tuple-invalid': tuple(),
            'set-invalid': set(),
            'list-invalid': [],
        }
        out = flattener(fieldmap)({})
        eq_(len(out.keys()), 0)
        fieldmap = {
            0.0: 'float-invalid',
        }
        out = flattener(fieldmap)({})
        eq_(len(out.keys()), 0)

    def test_default(self):
        fieldmap = {'x': 'x', 'y.a': 'y.a', 'y.1': 'y.1', 'z.a': 'z.a', '1': 1}
        default = 1
        flat = flattener(fieldmap, default=default)
        out = flat({'z': {}, 'y': []})
        eq_(out, {key: default for key in fieldmap})


class TestOnce(unittest.TestCase):
    def test_once(self):
        for key in ['►', 'λ', '►', 'λ']:
            eq_(once(key, _clear=True), None)
            eq_(once(key), True)
            eq_(once(key), False)
            eq_(once(key), False)
