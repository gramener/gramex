import yaml
import unittest
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader

from gramex.transforms import build_transform, _identity, badgerfish


def yaml_parse(text):
    return yaml.load(text, Loader=AttrDictYAMLLoader)


class BuildTransform(unittest.TestCase):
    'Test gramex.transforms.build_transform'

    def eqfn(self, a, b, msg=None):
        a_code, b_code = a.__code__, b.__code__
        for attr in ('co_code', 'co_argcount', 'co_nlocals'):
            self.assertEqual(
                getattr(a_code, attr),
                getattr(b_code, attr),
                msg + ': ' + attr[3:]
            )

    def test_identity(self):
        'function: defaults to lambda x: x'
        def transform(_val):
            return _identity(_val)
        fn = build_transform({})
        self.eqfn(fn, transform, 'test_identity')

    def test_fn(self):
        def transform(_val):
            return len(_val)
        fn = build_transform(yaml_parse('''
            function: len
        '''))
        self.eqfn(fn, transform, 'test_fn')

    def test_fn_args(self):
        def transform(_val):
            return max(1, 2)
        fn = build_transform(yaml_parse('''
            function: max
            args: [1, 2]
        '''))
        self.eqfn(fn, transform, 'test_fn_args')

    def test_fn_args_var(self):
        def transform(x=1, y=2):
            return max(x, y, 3)
        fn = build_transform(yaml_parse('''
            function: max
            args:
                - =x
                - =y
                - 3
        '''), vars=AttrDict([('x', 1), ('y', 2)]))
        self.eqfn(fn, transform, 'test_fn_args_var')

    def test_fn_kwargs(self):
        def transform(_val):
            return dict(_val, a=1, b=2)
        fn = build_transform(yaml_parse('''
            function: dict
            kwargs: {a: 1, b: 2}
        '''))
        self.eqfn(fn, transform, 'test_fn_kwargs')

    def test_fn_kwargs_complex(self):
        def transform(_val):
            return dict(_val, a=[1, 2], b=AttrDict([('b1', 'x'), ('b2', 'y')]))
        fn = build_transform(yaml_parse('''
            function: dict
            kwargs:
                a: [1, 2]
                b:
                    b1: x
                    b2: y
        '''))
        self.eqfn(fn, transform, 'test_fn_kwargs')

    def test_fn_kwargs_var(self):
        def transform(x=1, y=2):
            return dict(x, y, a=x, b=y, c=3)
        fn = build_transform(yaml_parse('''
            function: dict
            kwargs: {a: =x, b: =y, c: 3}
        '''), vars=AttrDict([('x', 1), ('y', 2)]))
        self.eqfn(fn, transform, 'test_fn_kwargs_var')

    def test_fn_args_kwargs(self):
        def transform(_val):
            return format(1, 2, a=3, b=4, c=5)
        fn = build_transform(yaml_parse('''
            function: format
            args: [1, 2]
            kwargs: {a: 3, b: 4, c: 5}
        '''))
        self.eqfn(fn, transform, 'test_fn_args_kwargs')

    def test_fn_args_kwargs_var(self):
        def transform(x=1, y=2):
            return format(x, y, a=x, b=y, c=3)
        fn = build_transform(yaml_parse('''
            function: format
            args: [=x, =y]
            kwargs: {a: =x, b: =y, c: =3}
        '''), vars=AttrDict([('x', 1), ('y', 2)]))
        self.eqfn(fn, transform, 'test_fn_args_kwargs_var')


class Badgerfish(unittest.TestCase):
    'Test gramex.transforms.badgerfish'

    def test_transform(self):
        self.assertEqual(badgerfish('''
        html:
          "@lang": en
          p: text
          div:
            p: text
        '''), '<!DOCTYPE html>\n<html lang="en"><p>text</p><div><p>text</p></div></html>')

    def test_mapping(self):
        result = badgerfish('''
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
