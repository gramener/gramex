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
        fn = build_transform({'function': 'string.lower'})
        self.assertEqual(fn('ABC'), 'abc')
        self.assertEqual(fn('aBc'), 'abc')

        fn = build_transform({'function': 'six.moves.builtins.sum'})
        self.assertEqual(fn([1, 2, 3]), 6)

    def test_args(self):
        'args: passed as positional arguments. _ represents input'
        # Splits content by comma
        fn = build_transform({
            'function': 'string.split',
            'args': ['_', ',']})
        self.assertEqual(fn('a,b,c'), ['a', 'b', 'c'])

        # Splits "abcdeabcdeabcde" with content
        fn = build_transform({
            'function': 'string.split',
            'args': ['abcdeabcdeabcde', '_']})
        self.assertEqual(fn('a'), ['', 'bcde', 'bcde', 'bcde'])
        self.assertEqual(fn('b'), ['a', 'cdea', 'cdea', 'cde'])

        # string.lower(), if called without arguments, raises TypeError
        fn = build_transform({
            'function': 'string.lower',
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
            }})
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
