from __future__ import unicode_literals

import io
import os
import json
import time
import yaml
import unittest
import gramex.cache
import pandas as pd
from six import string_types
from collections import OrderedDict
from orderedattrdict import AttrDict
from tornado.template import Template
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from pandas.util.testing import assert_frame_equal

folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_cache')


def touch(path, times=None):
    with io.open(path, 'ab'):
        os.utime(path, times)


class TestReloadModule(unittest.TestCase):
    '''Test gramex.cache.reload_module'''

    def test_reload_module(self):
        # When loaded, the counter is not incremented
        from testlib.test_cache.common import val
        self.assertEqual(val[0], 0)

        # On first load, the counter is incremented once
        import testlib.test_cache.mymodule
        self.assertEqual(val[0], 1)

        # On second load, it stays cached
        import testlib.test_cache.mymodule      # noqa
        self.assertEqual(val[0], 1)

        # The first time, we get the reloaded date. The module may be reloaded
        gramex.cache.reload_module(testlib.test_cache.mymodule)
        count = val[0]
        # On explicit reload_module, it still stays cached
        gramex.cache.reload_module(testlib.test_cache.mymodule)
        self.assertEqual(val[0], count)

        # Change the module
        pyfile = testlib.test_cache.mymodule.__file__.rstrip('c')
        module_timestamp_delay = 0.005
        time.sleep(module_timestamp_delay)
        touch(pyfile)

        # Regular import does not reload
        import testlib.test_cache.mymodule
        self.assertEqual(val[0], count)

        # ... but reload_module DOES reload, and the counter increments
        gramex.cache.reload_module(testlib.test_cache.mymodule)
        self.assertEqual(val[0], count + 1)

        # Subsequent call does not reload
        gramex.cache.reload_module(testlib.test_cache.mymodule)
        self.assertEqual(val[0], count + 1)


class TestOpen(unittest.TestCase):
    '''Test gramex.cache.open'''

    @staticmethod
    def check_file_cache(path, check):
        check(reload=True)
        check(reload=False)
        touch(path)
        check(reload=True)

    def test_open_csv(self):
        path = os.path.join(folder, 'data.csv')
        expected = pd.read_csv(path, encoding='utf-8')

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True,
                                                 encoding='utf-8')
            self.assertEqual(reloaded, reload)
            assert_frame_equal(result, expected)

        self.check_file_cache(path, check)

    def test_open_json(self):
        path = os.path.join(folder, 'data.json')
        with io.open(path, encoding='utf-8') as handle:
            expected = json.load(handle, object_pairs_hook=OrderedDict)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'json', _reload_status=True,
                                                 object_pairs_hook=OrderedDict)
            self.assertEqual(reloaded, reload)
            self.assertTrue(isinstance(result, OrderedDict))
            self.assertEqual(result, expected)

        self.check_file_cache(path, check)

    def test_open_yaml(self):
        path = os.path.join(folder, 'data.yaml')
        with io.open(path, encoding='utf-8') as handle:
            expected = yaml.load(handle, Loader=AttrDictYAMLLoader)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'yaml', _reload_status=True,
                                                 Loader=AttrDictYAMLLoader)
            self.assertEqual(reloaded, reload)
            self.assertTrue(isinstance(result, AttrDict))
            self.assertEqual(result, expected)

        self.check_file_cache(path, check)

    def test_open_template(self):
        path = os.path.join(folder, 'template.txt')
        with io.open(path, encoding='utf-8') as handle:
            expected = Template(handle.read(), autoescape=None)

        def check(reload):
            result, reloaded = gramex.cache.open(
                path, 'template', _reload_status=True, encoding='utf-8', autoescape=None)
            self.assertEqual(reloaded, reload)
            self.assertTrue(isinstance(result, Template))
            self.assertEqual(result.generate(name='x'), expected.generate(name='x'))
            self.assertEqual(result.generate(name='x'), b'<b>x</b>\n')

        self.check_file_cache(path, check)

    def test_custom_cache(self):
        path = os.path.join(folder, 'data.csv')
        cache = {}
        result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True, _cache=cache)
        self.assertTrue((path, 'csv') in cache)

        # Initially, the file is loaded
        self.assertEqual(reloaded, True)

        # Next time, it's loaded from the cache
        result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True, _cache=cache)
        self.assertEqual(reloaded, False)

        # If the cache is deleted, it reloads
        del cache[path, 'csv']
        result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True, _cache=cache)
        self.assertEqual(reloaded, True)

    def test_multiple_loaders(self):
        # Loading the same file via different callbacks should return different results
        path = os.path.join(folder, 'multiformat.csv')
        data = gramex.cache.open(path, 'csv')
        self.assertTrue(isinstance(data, pd.DataFrame))
        text = gramex.cache.open(path, 'text')
        self.assertTrue(isinstance(text, string_types))
        none = gramex.cache.open(path, lambda path: None)
        self.assertTrue(none is None)
