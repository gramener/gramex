import unittest
from gramex.transforms import build_transform, badgerfish


class BuildTransform(unittest.TestCase):
    'Test gramex.transforms.build_transform'

    def test_identity(self):
        'function: defaults to lambda x: x'
        fn = build_transform({})
        self.assertEqual(fn(1), 1)
        self.assertEqual(fn('x'), 'x')
        with self.assertRaises(TypeError):
            fn(1, 2)

    def test_function(self):
        fn = build_transform({'function': 'str.lower'})
        self.assertEqual(fn('ABC'), 'abc')
        self.assertEqual(fn('aBc'), 'abc')

        fn = build_transform({'function': 'sum'})
        self.assertEqual(fn([1, 2, 3]), 6)

    def test_args(self):
        'args: passed as positional arguments'

        # Arguments are taken explicitly by default
        join = build_transform({'function': 'str.join', 'args': [',', ['a', 'b']]})
        self.assertEqual(join('anything'), 'a,b')

        # Single input variable is replaced in args
        join = build_transform({
                   'function': 'str.join',
                   'args': ['|', 'input']},
                   vars='input')
        self.assertEqual(join(['a', 'b', 'c']), 'a|b|c')

        # Multiple input variables are replaced in args
        join = build_transform({
            'function': 'str.join',
            'args': ['separator', 'string_list']},
            vars=['separator', 'string_list'])
        self.assertEqual(join(string_list=['a', 'b', 'c'], separator=','), 'a,b,c')

        # args defaults to vars
        join = build_transform({'function': 'str.join'}, vars=['sep', 'str'])
        self.assertEqual(join(',', ['a', 'b', 'c']), 'a,b,c')

        # args can have a different order than vars
        join = build_transform({
            'function': 'str.join',
            'args': ['sep', 'list']},
            vars=['list', 'sep'])
        self.assertEqual(join(['a', 'b', 'c'], ','), 'a,b,c')

        # args can be explicit strings, and a subset of the vars
        join = build_transform({
            'function': 'str.join',
            'args': [',', 'list']},
            vars=['sep', 'list'])
        self.assertEqual(join(sep='anything', list=['a', 'b', 'c']), 'a,b,c')

        # str.lower(), if called without arguments, raises TypeError
        fn = build_transform({
            'function': 'str.lower',
            'args': []})
        with self.assertRaises(TypeError):
            fn('ABC')

        # random.random() is called without arguments
        fn = build_transform({
            'function': 'random.random',
            'args': []})
        result = fn(100)
        self.assertLessEqual(result, 1)
        self.assertGreaterEqual(result, 0)

    def test_kwargs(self):
        'kwargs: passed as keyword arguments. _ represents input'
        fn = build_transform({
            'function': 'json.dumps',
            'args': [],
            'kwargs': {
                'obj': '_',
                'separators': [',', ':'],
            }}, vars='_')
        self.assertEqual(fn([1, 2]), "[1,2]")


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
