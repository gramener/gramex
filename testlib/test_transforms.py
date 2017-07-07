from __future__ import print_function, unicode_literals
import io
import os
import yaml
import inspect
import unittest
from dis import dis
from types import GeneratorType
from tornado.gen import coroutine, Task
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from gramex.transforms import build_transform, flattener, badgerfish, template
from gramex.cache import reload_module


def yaml_parse(text):
    return yaml.load(text, Loader=AttrDictYAMLLoader)


def remove(path):
    if os.path.exists(path):
        os.unlink(path)


@coroutine
def gen_str(val):
    'Sample coroutine method'
    yield Task(str, val)


class BuildTransform(unittest.TestCase):
    '''Test build_transform CODE output'''
    folder = os.path.dirname(os.path.abspath(__file__))
    files = set()

    def eqfn(self, a, b):
        a_code, b_code = a.__code__, b.__code__

        # msg = parent function's name
        msg = inspect.stack()[1][3]

        src, tgt = a_code.co_code, b_code.co_code
        if src != tgt:
            # Print the disassembled code to make debugging easier
            print('\nCompiled by build_transform from YAML')    # noqa
            dis(src)
            print(a_code.co_names)                              # noqa
            print('Tested against test case')                   # noqa
            dis(tgt)
            print(b_code.co_names)                              # noqa
        self.assertEqual(src, tgt, '%s: code mismatch' % msg)

        src, tgt = a_code.co_argcount, b_code.co_argcount
        self.assertEqual(src, tgt, '%s: argcount %d != %d' % (msg, src, tgt))
        src, tgt = a_code.co_nlocals, b_code.co_nlocals
        self.assertEqual(src, tgt, '%s: nlocals %d != %d' % (msg, src, tgt))

    def check_transform(self, transform, yaml_code, vars=None, cache=True):
        fn = build_transform(yaml_parse(yaml_code), vars=vars, cache=cache)
        self.eqfn(fn, transform)
        return fn

    def test_invalid_function_raises_error(self):
        with self.assertRaises(KeyError):
            build_transform({})
        with self.assertRaises(KeyError):
            build_transform({'function': ''})
        with self.assertRaises(ValueError):
            build_transform({'function': 'x = 1'})
        with self.assertRaises(ValueError):
            build_transform({'function': 'x(); y()'})
        with self.assertRaises(ValueError):
            build_transform({'function': 'import json'})

    def test_expr(self):
        def transform(x=0):
            result = x + 1
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, 'function: x + 1', vars={'x': 0})

        def transform():
            result = "abc"
            return result if isinstance(result, GeneratorType) else [result, ]
        self.check_transform(transform, '''function: '"abc"' ''', vars={})

        def transform():
            import gramex.cache, pandas     # noqa: build_transform does this
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
        dummy = os.path.join(self.folder, 'dummy.py')
        self.files.add(dummy)
        remove(dummy.replace('.py', '.pyc'))
        with io.open(dummy, 'w', encoding='utf-8') as handle:
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
        self.assertEqual(fn(), [1])
        fn = self.check_transform(transform, 'function: testlib.dummy.value()', cache=False)
        self.assertEqual(fn(), [1])

        remove(dummy.replace('.py', '.pyc'))
        with io.open(dummy, 'w', encoding='utf-8') as handle:
            handle.write('def value():\n\treturn 100\n')
        self.assertEqual(fn(), [100])
        fn = self.check_transform(transform, 'function: testlib.dummy.value()', cache=False)
        self.assertEqual(fn(), [100])

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
        self.assertEqual(
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
        self.assertEqual(
            result,
            '<!DOCTYPE html>\n<html><json>{"x":1,"y":2}</json></html>')


class Template(unittest.TestCase):
    'Test gramex.transforms.template'
    def check(self, content, expected, **kwargs):
        result = yield template(content, **kwargs)
        self.assertEqual(result, expected)

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
        self.assertEqual(out.keys(), fieldmap.keys())
        self.assertEqual(out['all1'], src)
        self.assertEqual(out['all2'], src)
        self.assertEqual(out['x'], src['x'])
        self.assertEqual(out['y.z'], src['y']['z'])
        self.assertEqual(out['z.1'], src['z'][1])

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
        self.assertEqual(out.keys(), fieldmap.keys())
        self.assertEqual(out['0'], src[0])
        self.assertEqual(out['1'], src[1])
        self.assertEqual(out['2.0'], src[2][0])

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
        self.assertEqual(len(out.keys()), 0)
        fieldmap = {
            0.0: 'float-invalid',
        }
        out = flattener(fieldmap)({})
        self.assertEqual(len(out.keys()), 0)

    def test_default(self):
        fieldmap = {'x': 'x', 'y.a': 'y.a', 'y.1': 'y.1', 'z.a': 'z.a', '1': 1}
        default = 1
        flat = flattener(fieldmap, default=default)
        out = flat({'z': {}, 'y': []})
        self.assertEqual(out, {key: default for key in fieldmap})
