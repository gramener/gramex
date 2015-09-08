import os
import yaml
import unittest
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from gramex.confutil import python_name, walk


class TestConfUtil(unittest.TestCase):
    def test_python_name(self):
        'Test gramex.confutil.python_name'

        # Blank values raise NameError
        with self.assertRaises(NameError):
            python_name('')
        # Non-existent builtins raise NameError
        with self.assertRaises(NameError):
            python_name('no-such-builtin')
        # Non-existent members raise NameError
        with self.assertRaises(NameError):
            python_name('os.no-such-value')
        # Non-existent modules
        with self.assertRaises(NameError):
            python_name('no-such-module.__name__')

        # Test valid values
        self.assertEqual(python_name('sum'), sum)
        self.assertEqual(python_name('os.path.exists'), os.path.exists)
        self.assertEqual(python_name('unittest.TestCase'), unittest.TestCase)
        self.assertEqual(python_name('gramex.confutil.walk'), walk)

    def test_walk(self):
        'Test gramex.confutil.walk'
        o = yaml.load('''
            a:
                b:
                    c: 1
                    d: 2
                e: 3
                f:
                    g:
                        h: 4
                        i: 5
                j: 6
            k: 7
        ''', Loader=AttrDictYAMLLoader)
        result = list(walk(o))
        self.assertEqual(
            [key for key, val, node in result],
            list('abcdefghijk'))
        self.assertEqual(
            [val for key, val, node in result],
            [o.a, o.a.b, o.a.b.c, o.a.b.d, o.a.e, o.a.f, o.a.f.g, o.a.f.g.h,
             o.a.f.g.i, o.a.j, o.k])
        self.assertEqual(
            [node for key, val, node in result],
            [o, o.a, o.a.b, o.a.b, o.a, o.a, o.a.f, o.a.f.g,
             o.a.f.g, o.a, o])
