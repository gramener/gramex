import io
import os
import time
import unittest
import gramex.cache
import pandas as pd
import sqlalchemy as sa
from gramex.config import variables
from nose.tools import eq_, assert_raises
from orderedattrdict import AttrDict
from . import folder, dbutils, afe

cache_folder = os.path.join(folder, 'test_cache')
state_file = os.path.join(cache_folder, '.state')
small_delay = 0.01


def touch(path, times=None, data=None):
    with io.open(path, 'ab') as handle:
        os.utime(path, times)
        if data is not None:
            handle.write(data)


class TestReloadModule(unittest.TestCase):
    def test_reload_module(self):
        # When loaded, the counter is not incremented
        from testlib.test_cache.common import val

        eq_(val[0], 0)

        # On first load, the counter is incremented once
        import testlib.test_cache.mymodule

        eq_(val[0], 1)

        # On second load, it stays cached
        import testlib.test_cache.mymodule  # noqa

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


class TestOpener(unittest.TestCase):
    def check_args(self, *args, **kwargs):
        return AttrDict(args=args, kwargs=kwargs)

    def test_params(self):
        # gramex.cache.opener should have a callable callback
        with assert_raises(ValueError):
            gramex.cache.opener(None)
        with assert_raises(ValueError):
            gramex.cache.opener('text')

    def test_opener(self):
        o = gramex.cache.opener(self.check_args)
        path = os.path.join(cache_folder, 'template.txt')

        result = o(path)
        eq_(type(result.args[0]), io.TextIOWrapper)
        eq_(result.args[0].name, path)
        eq_(result.args[0].encoding, 'utf-8')
        eq_(result.kwargs, {})

        result = o(path, encoding='cp1252')
        eq_(type(result.args[0]), io.TextIOWrapper)
        eq_(result.args[0].encoding, 'cp1252')
        eq_(result.kwargs, {})

        result = o(path, mode='rb', encoding=None, errors=None)
        eq_(type(result.args[0]), io.BufferedReader)
        eq_(result.kwargs, {})

        result = o(path, num=1, s='a', none=None)
        eq_(result.kwargs, {'num': 1, 's': 'a', 'none': None})

    def test_reader(self):
        o = gramex.cache.opener(self.check_args, read=True)
        path = os.path.join(cache_folder, 'template.txt')

        with io.open(path, encoding='utf-8') as handle:
            text = handle.read()
        result = o(path)
        eq_(result.args, (text,))
        eq_(result.kwargs, {})

        with io.open(path, mode='rb') as handle:
            text = handle.read()
        result = o(path, mode='rb', encoding=None, errors=None)
        eq_(result.args, (text,))
        eq_(result.kwargs, {})

        result = o(path, num=1, s='a', none=None)
        eq_(result.kwargs, {'num': 1, 's': 'a', 'none': None})


class TestSqliteCacheQuery(unittest.TestCase):
    data = pd.read_csv(os.path.join(cache_folder, 'data.csv'), encoding='utf-8')
    states = [['t1'], 'SELECT COUNT(*) FROM t1', lambda: gramex.cache.stat(state_file)]

    @classmethod
    def setUpClass(cls):
        cls.url = dbutils.sqlite_create_db('test_cache.db', t1=cls.data, t2=cls.data)
        cls.engine = sa.create_engine(cls.url, encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        dbutils.sqlite_drop_db('test_cache')

    def test_wheres(self):
        w = gramex.cache._wheres
        eq_(w('db', 'tbl', 'db', ['x']), "(db='db' AND tbl='x')")
        eq_(w('db', 'tbl', 'db', ['x', 'y']), "(db='db' AND tbl='x') OR (db='db' AND tbl='y')")
        eq_(w('db', 'tbl', 'db', ['a.x']), "(db='a' AND tbl='x')")
        eq_(w('db', 'tbl', 'db', ['a.x', 'y']), "(db='a' AND tbl='x') OR (db='db' AND tbl='y')")
        eq_(w('db', 'tbl', 'db', ['a.x', 'b.y']), "(db='a' AND tbl='x') OR (db='b' AND tbl='y')")

    def test_query_state_invalid(self):
        # Empty state list raises an error
        with assert_raises(ValueError):
            gramex.cache.query('SELECT * FROM t1', self.engine, state=[])
        # State list with invalid type raises an error
        with assert_raises(ValueError):
            gramex.cache.query('SELECT * FROM t1', self.engine, state=[None])
        # Anything other than a string, list/tuple or function should raise a TypeError
        with assert_raises(TypeError):
            gramex.cache.query('SELECT * FROM t1', self.engine, state=1)

    def test_query_value(self):
        afe(gramex.cache.query('SELECT * FROM t2', engine=self.engine), self.data)

    def test_query_cache(self):
        sql = 'SELECT * FROM t1 LIMIT 2'
        kwargs = {'sql': sql, 'engine': self.engine, 'state': ['t1'], '_reload_status': True}
        c0 = len(gramex.cache._QUERY_CACHE)
        eq_(gramex.cache.query(**kwargs)[1], True)
        c1 = len(gramex.cache._QUERY_CACHE)
        eq_(gramex.cache.query(**kwargs)[1], False)
        c2 = len(gramex.cache._QUERY_CACHE)
        eq_(c1, c0 + 1)
        eq_(c1, c2)

    def test_query_states(self):
        # Check for 3 combinations
        # 1. state is a list of table names. (Currently, this only works with sqlite)
        # 2. state is a string (query to check row count)
        # 3. state is a callable (checks updated time of .state file)
        for state in self.states:
            msg = 'failed at state=%s, url=%s' % (state, self.url)
            sql = 'SELECT * FROM t1'
            kwargs = {'sql': sql, 'engine': self.engine, 'state': state, '_reload_status': True}
            eq_(gramex.cache.query(**kwargs)[1], True, msg)
            eq_(gramex.cache.query(**kwargs)[1], False, msg)
            eq_(gramex.cache.query(**kwargs)[1], False, msg)

            # Update the data
            if callable(state):
                touch(state_file, data=b'x')
            else:
                self.data.to_sql('t1', self.engine, if_exists='append', index=False)

            eq_(gramex.cache.query(**kwargs)[1], True, msg)
            eq_(gramex.cache.query(**kwargs)[1], False, msg)
            eq_(gramex.cache.query(**kwargs)[1], False, msg)

        # If state is None, always reload the query
        kwargs['state'] = None
        eq_(gramex.cache.query(**kwargs)[1], True, msg)
        eq_(gramex.cache.query(**kwargs)[1], True, msg)
        eq_(gramex.cache.query(**kwargs)[1], True, msg)


class TestMySQLCacheQuery(TestSqliteCacheQuery):
    states = ['SELECT COUNT(*) FROM t1', lambda: gramex.cache.stat(state_file)]

    @classmethod
    def setUpClass(cls):
        cls.url = dbutils.mysql_create_db(
            variables.MYSQL_SERVER, 'test_cache', t1=cls.data, t2=cls.data
        )
        cls.engine = sa.create_engine(cls.url, encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        dbutils.mysql_drop_db(variables.MYSQL_SERVER, 'test_cache')


class TestPostgresCacheQuery(TestSqliteCacheQuery):
    states = ['SELECT COUNT(*) FROM t1', lambda: gramex.cache.stat(state_file)]

    @classmethod
    def setUpClass(cls):
        cls.url = dbutils.postgres_create_db(
            variables.POSTGRES_SERVER,
            'test_cache',
            **{'t1': cls.data, 't2': cls.data, 'sc.t3': cls.data},
        )
        cls.engine = sa.create_engine(cls.url, encoding='utf-8')

    def test_schema(self):
        afe(gramex.cache.query('SELECT * FROM sc.t3', engine=self.engine), self.data)

    @classmethod
    def tearDownClass(cls):
        dbutils.postgres_drop_db(variables.POSTGRES_SERVER, 'test_cache')


def tearDownModule():
    if os.path.exists(state_file):
        os.unlink(state_file)
