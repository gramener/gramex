from __future__ import unicode_literals

import io
import os
import six
import json
import time
import yaml
import unittest
import gramex.cache
import pandas as pd
import sqlalchemy as sa
from gramex.config import variables
from tests import dbutils
from six import string_types
from markdown import markdown
from collections import OrderedDict
from orderedattrdict import AttrDict
from tornado.template import Template
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from pandas.util.testing import assert_frame_equal
from nose.tools import eq_, ok_, assert_raises

folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_cache')


def touch(path, times=None, data=None):
    with io.open(path, 'ab') as handle:
        os.utime(path, times)
        if data is not None:
            handle.write(data)


class TestReloadModule(unittest.TestCase):
    '''Test gramex.cache.reload_module'''

    def test_reload_module(self):
        # When loaded, the counter is not incremented
        from testlib.test_cache.common import val
        eq_(val[0], 0)

        # On first load, the counter is incremented once
        import testlib.test_cache.mymodule
        eq_(val[0], 1)

        # On second load, it stays cached
        import testlib.test_cache.mymodule      # noqa
        eq_(val[0], 1)

        # The first time, we get the reloaded date. The module may be reloaded
        gramex.cache.reload_module(testlib.test_cache.mymodule)
        count = val[0]
        # On explicit reload_module, it still stays cached
        gramex.cache.reload_module(testlib.test_cache.mymodule)
        eq_(val[0], count)

        # Change the module
        pyfile = testlib.test_cache.mymodule.__file__.rstrip('c')
        module_timestamp_delay = 0.005
        time.sleep(module_timestamp_delay)
        touch(pyfile)

        # Regular import does not reload
        import testlib.test_cache.mymodule
        eq_(val[0], count)

        # ... but reload_module DOES reload, and the counter increments
        gramex.cache.reload_module(testlib.test_cache.mymodule)
        eq_(val[0], count + 1)

        # Subsequent call does not reload
        gramex.cache.reload_module(testlib.test_cache.mymodule)
        eq_(val[0], count + 1)


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
            eq_(reloaded, reload)
            assert_frame_equal(result, expected)

        self.check_file_cache(path, check)

    def test_open_json(self):
        path = os.path.join(folder, 'data.json')
        with io.open(path, encoding='utf-8') as handle:
            expected = json.load(handle, object_pairs_hook=OrderedDict)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'json', _reload_status=True,
                                                 object_pairs_hook=OrderedDict)
            eq_(reloaded, reload)
            ok_(isinstance(result, OrderedDict))
            eq_(result, expected)

        self.check_file_cache(path, check)

    def test_open_yaml(self):
        path = os.path.join(folder, 'data.yaml')
        with io.open(path, encoding='utf-8') as handle:
            expected = yaml.load(handle, Loader=AttrDictYAMLLoader)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'yaml', _reload_status=True,
                                                 Loader=AttrDictYAMLLoader)
            eq_(reloaded, reload)
            ok_(isinstance(result, AttrDict))
            eq_(result, expected)

        self.check_file_cache(path, check)

    def test_open_template(self):
        path = os.path.join(folder, 'template.txt')
        with io.open(path, encoding='utf-8') as handle:
            expected = Template(handle.read(), autoescape=None)

        def check(reload):
            result, reloaded = gramex.cache.open(
                path, 'template', _reload_status=True, encoding='utf-8', autoescape=None)
            eq_(reloaded, reload)
            ok_(isinstance(result, Template))
            eq_(result.generate(name='x'), expected.generate(name='x'))
            eq_(result.generate(name='x'), b'<b>x</b>\n')

        self.check_file_cache(path, check)

    def test_open_markdown(self):
        path = os.path.join(folder, 'markdown.md')
        extensions = [
            'markdown.extensions.codehilite',
            'markdown.extensions.extra',
            'markdown.extensions.headerid',
            'markdown.extensions.meta',
            'markdown.extensions.sane_lists',
            'markdown.extensions.smarty',
        ]
        with io.open(path, encoding='utf-8') as handle:
            expected = markdown(handle.read(), output_format='html5', extensions=extensions)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'md', _reload_status=True, encoding='utf-8')
            eq_(reloaded, reload)
            ok_(isinstance(result, six.text_type))
            eq_(result, expected)

        self.check_file_cache(path, check)

    def test_custom_cache(self):
        path = os.path.join(folder, 'data.csv')
        cache = {}
        result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True, _cache=cache)
        ok_((path, 'csv') in cache)

        # Initially, the file is loaded
        eq_(reloaded, True)

        # Next time, it's loaded from the cache
        result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True, _cache=cache)
        eq_(reloaded, False)

        # If the cache is deleted, it reloads
        del cache[path, 'csv']
        result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True, _cache=cache)
        eq_(reloaded, True)

    def test_multiple_loaders(self):
        # Loading the same file via different callbacks should return different results
        path = os.path.join(folder, 'multiformat.csv')
        data = gramex.cache.open(path, 'csv')
        ok_(isinstance(data, pd.DataFrame))
        text = gramex.cache.open(path, 'text')
        ok_(isinstance(text, string_types))
        none = gramex.cache.open(path, lambda path: None)
        ok_(none is None)


class TestCacheQuery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = cls.data = pd.read_csv(os.path.join(folder, 'data.csv'), encoding='utf-8')
        cls.urls = [
            dbutils.mysql_create_db(variables.MYSQL_SERVER, 'test_cache', t1=data, t2=data),
            dbutils.postgres_create_db(variables.POSTGRES_SERVER, 'test_cache', t1=data, t2=data),
            dbutils.sqlite_create_db('test_cache.db', t1=data, t2=data),
        ]
        cls.state = os.path.join(folder, '.state')

    def test_wheres(self):
        w = gramex.cache._wheres
        eq_(w('db', 'tbl', 'db', ['x']), "(db='db' AND tbl='x')")
        eq_(w('db', 'tbl', 'db', ['x', 'y']), "(db='db' AND tbl='x') OR (db='db' AND tbl='y')")
        eq_(w('db', 'tbl', 'db', ['a.x']), "(db='a' AND tbl='x')")
        eq_(w('db', 'tbl', 'db', ['a.x', 'y']), "(db='a' AND tbl='x') OR (db='db' AND tbl='y')")
        eq_(w('db', 'tbl', 'db', ['a.x', 'b.y']), "(db='a' AND tbl='x') OR (db='b' AND tbl='y')")

    def test_query_state_invalid(self):
        # Just take the sqlite URL for now
        engine = sa.create_engine(self.urls[-1], encoding='utf-8')
        with assert_raises(ValueError, 'Empty state list raises an error'):
            gramex.cache.query('SELECT * FROM t1', engine, state=[])
        with assert_raises(ValueError, 'State list with invalid type raises an error'):
            gramex.cache.query('SELECT * FROM t1', engine, state=[None])

    def test_query_states(self):
        # Check for 3 combinations
        # 1. state is a list of table names. (Currently, this only works with sqlite)
        # 2. state is a string (query to check row count)
        # 3. state is a callable (checks updated time of .state file)
        combinations = [
            dict(state=['t1'], urls=[url for url in self.urls if url.startswith('sqlite')]),
            dict(state='SELECT COUNT(*) FROM t1', urls=self.urls),
            dict(state=lambda: gramex.cache.stat(self.state), urls=self.urls),
        ]
        sql = 'SELECT * FROM t1'
        for row in combinations:
            for url in row['urls']:
                msg = 'failed at state=%s, url=%s' % (row['state'], url)
                engine = sa.create_engine(url, encoding='utf-8')
                kwargs = dict(sql=sql, engine=engine, state=row['state'], _reload_status=True)
                eq_(gramex.cache.query(**kwargs)[1], True, msg)
                eq_(gramex.cache.query(**kwargs)[1], False, msg)
                eq_(gramex.cache.query(**kwargs)[1], False, msg)

                # Update the data
                if callable(row['state']):
                    touch(self.state, data=b'x')
                else:
                    self.data.to_sql('t1', engine, if_exists='append', index=False)

                eq_(gramex.cache.query(**kwargs)[1], True, msg)
                eq_(gramex.cache.query(**kwargs)[1], False, msg)
                eq_(gramex.cache.query(**kwargs)[1], False, msg)

    @classmethod
    def tearDownClass(cls):
        dbutils.mysql_drop_db(variables.MYSQL_SERVER, 'test_cache')
        dbutils.postgres_drop_db(variables.POSTGRES_SERVER, 'test_cache')
        dbutils.sqlite_drop_db('test_cache.db')
        if os.path.exists(cls.state):
            os.unlink(cls.state)
