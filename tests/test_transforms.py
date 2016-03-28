from __future__ import print_function
import yaml
import inspect
import unittest
from dis import dis
from tornado.concurrent import is_future
from tornado.gen import coroutine, Return, Task
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from gramex.transforms import build_transform, badgerfish


def _build_transform(conf, vars=None):
    return build_transform(conf, vars, _coroutine=False)


def yaml_parse(text):
    return yaml.load(text, Loader=AttrDictYAMLLoader)


@coroutine
def gen_str(val):
    'Sample coroutine method'
    yield Task(str, val)


class BuildTransform(unittest.TestCase):
    'Test gramex.transforms.build_transform'

    def eqfn(self, a, b):
        a_code, b_code = a.__code__, b.__code__

        # msg = parent function's name
        msg = inspect.stack()[1][3]

        src, tgt = a_code.co_code, b_code.co_code
        if src != tgt:
            # Print the disassembled code to make debugging easier
            print('Compiled by build_transform from YAML')
            dis(src)
            print('Tested against test case')
            dis(tgt)
        self.assertEqual(src, tgt, '%s: code mismatch' % msg)

        src, tgt = a_code.co_argcount, b_code.co_argcount
        self.assertEqual(src, tgt, '%s: argcount %d != %d' % (msg, src, tgt))
        src, tgt = a_code.co_nlocals, b_code.co_nlocals
        self.assertEqual(src, tgt, '%s: nlocals %d != %d' % (msg, src, tgt))

    def test_no_function_raises_error(self):
        with self.assertRaises(KeyError):
            _build_transform({})

    def test_fn(self):
        def transform(_val):
            result = len(_val)
            if is_future(result):
                result = yield result
            raise Return(result)
        fn = _build_transform(yaml_parse('''
            function: len
        '''))
        self.eqfn(fn, transform)

    def test_fn_args(self):
        def transform(_val):
            result = max(1, 2)
            if is_future(result):
                result = yield result
            raise Return(result)
        fn = _build_transform(yaml_parse('''
            function: max
            args: [1, 2]
        '''))
        self.eqfn(fn, transform)

    def test_fn_args_var(self):
        def transform(x=1, y=2):
            result = max(x, y, 3)
            if is_future(result):
                result = yield result
            raise Return(result)
        fn = _build_transform(yaml_parse('''
            function: max
            args:
                - =x
                - =y
                - 3
        '''), vars=AttrDict([('x', 1), ('y', 2)]))
        self.eqfn(fn, transform)

    def test_fn_kwargs(self):
        def transform(_val):
            result = dict(_val, a=1, b=2)
            if is_future(result):
                result = yield result
            raise Return(result)
        fn = _build_transform(yaml_parse('''
            function: dict
            kwargs: {a: 1, b: 2}
        '''))
        self.eqfn(fn, transform)

    def test_fn_kwargs_complex(self):
        def transform(_val):
            result = dict(_val, a=[1, 2], b=AttrDict([('b1', 'x'), ('b2', 'y')]))
            if is_future(result):
                result = yield result
            raise Return(result)
        fn = _build_transform(yaml_parse('''
            function: dict
            kwargs:
                a: [1, 2]
                b:
                    b1: x
                    b2: y
        '''))
        self.eqfn(fn, transform)

    def test_fn_kwargs_var(self):
        def transform(x=1, y=2):
            result = dict(x, y, a=x, b=y, c=3)
            if is_future(result):
                result = yield result
            raise Return(result)
        fn = _build_transform(yaml_parse('''
            function: dict
            kwargs: {a: =x, b: =y, c: 3}
        '''), vars=AttrDict([('x', 1), ('y', 2)]))
        self.eqfn(fn, transform)

    def test_fn_args_kwargs(self):
        def transform(_val):
            result = format(1, 2, a=3, b=4, c=5)
            if is_future(result):
                result = yield result
            raise Return(result)
        fn = _build_transform(yaml_parse('''
            function: format
            args: [1, 2]
            kwargs: {a: 3, b: 4, c: 5}
        '''))
        self.eqfn(fn, transform)

    def test_fn_args_kwargs_var(self):
        def transform(x=1, y=2):
            result = format(x, y, a=x, b=y, c=3)
            if is_future(result):
                result = yield result
            raise Return(result)
        fn = _build_transform(yaml_parse('''
            function: format
            args: [=x, =y]
            kwargs: {a: =x, b: =y, c: =3}
        '''), vars=AttrDict([('x', 1), ('y', 2)]))
        self.eqfn(fn, transform)

    def test_coroutine(self):
        def transform(_val):
            result = gen_str(_val)
            if is_future(result):
                result = yield result
            raise Return(result)
        fn = _build_transform(yaml_parse('''
            function: tests.test_transforms.gen_str
        '''))
        self.eqfn(fn, transform)


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
