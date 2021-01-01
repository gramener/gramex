import io
import os
import re
import six
import json
import time
import yaml
import unittest
import gramex.cache
import pandas as pd
import sqlalchemy as sa
from lxml import etree
from gramex.cache import hashfn
from gramex.config import variables, str_utf8
from six import string_types
from markdown import markdown
from collections import OrderedDict
from orderedattrdict import AttrDict
from tornado.template import Template
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from pandas.util.testing import assert_frame_equal as afe
from nose.tools import eq_, ok_, assert_raises
import dbutils
from . import folder, tests_dir

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
        eq_(result.args, (text, ))
        eq_(result.kwargs, {})

        with io.open(path, mode='rb') as handle:
            text = handle.read()
        result = o(path, mode='rb', encoding=None, errors=None)
        eq_(result.args, (text, ))
        eq_(result.kwargs, {})

        result = o(path, num=1, s='a', none=None)
        eq_(result.kwargs, {'num': 1, 's': 'a', 'none': None})


class TestOpen(unittest.TestCase):
    @staticmethod
    def check_file_cache(path, check):
        check(reload=True)
        check(reload=False)
        touch(path)
        time.sleep(small_delay)
        check(reload=True)

    def test_rel(self):
        # Passing rel=True picks up the file from the current directory
        path = 'test_cache/template.txt'
        with io.open(os.path.join(cache_folder, 'template.txt'), encoding='utf-8') as handle:
            expected = handle.read()
        result = gramex.cache.open(path, 'txt', rel=True)
        eq_(result, expected)

    def test_open_text(self):
        path = os.path.join(cache_folder, 'template.txt')
        expected = io.open(path, encoding='utf-8', errors='ignore').read()

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'text', _reload_status=True)
            eq_(reloaded, reload)
            eq_(result, expected)

        self.check_file_cache(path, check)
        eq_(gramex.cache.open(path), gramex.cache.open(path, 'text'))
        eq_(gramex.cache.open(path), gramex.cache.open(path, 'txt'))

    def test_open_bin(self):
        path = os.path.join(cache_folder, 'data.bin')
        expected = io.open(path, mode='rb').read()

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'bin', _reload_status=True)
            eq_(reloaded, reload)
            eq_(result, expected)

        self.check_file_cache(path, check)

    def test_open_csv(self):
        path = os.path.join(cache_folder, 'data.csv')
        expected = pd.read_csv(path, encoding='utf-8')

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True,
                                                 encoding='utf-8')
            eq_(reloaded, reload)
            afe(result, expected)

        self.check_file_cache(path, check)
        afe(gramex.cache.open(path), gramex.cache.open(path, 'csv'))

    def test_xlsx(self):
        path = os.path.join(tests_dir, 'sales.xlsx')
        # Excel files are loaded via pd.read_excel by default
        afe(gramex.cache.open(path, sheet_name='sales'),
            pd.read_excel(path, sheet_name='sales', engine='openpyxl'))
        # Load range. sales!A1:E25 is the same as the sheet "sales"
        afe(gramex.cache.open(path, sheet_name='sales', range='A1:E25'),
            pd.read_excel(path, sheet_name='sales', engine='openpyxl'))
        # sheet_name defaults to 0
        afe(gramex.cache.open(path, range='A1:E25'), pd.read_excel(path, engine='openpyxl'))
        # sheet_name can be an int, not just a str
        afe(gramex.cache.open(path, sheet_name=1, range='A1:$B$34'),
            pd.read_excel(path, sheet_name=1, engine='openpyxl'))
        # header can be any int or list of int, passed directly to pd.read_excel
        afe(gramex.cache.open(path, sheet_name='sales', header=[0, 1], range='A$1:$E25'),
            pd.read_excel(path, sheet_name='sales', header=[0, 1], engine='openpyxl'))
        # header=None doesn't add a header
        afe(gramex.cache.open(path, sheet_name='sales', header=None, range='A$1:$E25'),
            pd.read_excel(path, sheet_name='sales', header=None, engine='openpyxl'))
        # Load table. "SalesTable" is the same as table!A1B11
        afe(gramex.cache.open(path, sheet_name='table', table='SalesTable'),
            gramex.cache.open(path, sheet_name='table', range='A1:$B$11'))
        afe(gramex.cache.open(path, sheet_name='table', table='CensusTable'),
            gramex.cache.open(path, sheet_name='table', range='$D1:F$23'))
        # Load named range. The "sales" named range is the same as the sheet "sales"
        afe(gramex.cache.open(path, sheet_name='sales', defined_name='sales'),
            gramex.cache.open(path, sheet_name='sales'))
        # Test failure conditions, edge cases, etc.

    def test_open_json(self):
        path = os.path.join(cache_folder, 'data.json')
        with io.open(path, encoding='utf-8') as handle:
            expected = json.load(handle, object_pairs_hook=OrderedDict)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'json', _reload_status=True,
                                                 object_pairs_hook=OrderedDict)
            eq_(reloaded, reload)
            ok_(isinstance(result, OrderedDict))
            eq_(result, expected)

        self.check_file_cache(path, check)
        eq_(gramex.cache.open(path), gramex.cache.open(path, 'json'))

    def test_open_jsondata(self):
        path = os.path.join(cache_folder, 'data.jsondata')
        expected = pd.read_json(path)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'jsondata', _reload_status=True)
            eq_(reloaded, reload)
            afe(result, expected)

        self.check_file_cache(path, check)
        afe(gramex.cache.open(path), gramex.cache.open(path, 'jsondata'))

    def test_open_yaml(self):
        path = os.path.join(cache_folder, 'data.yaml')
        with io.open(path, encoding='utf-8') as handle:
            expected = yaml.load(handle, Loader=AttrDictYAMLLoader)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'yaml', _reload_status=True,
                                                 Loader=AttrDictYAMLLoader)
            eq_(reloaded, reload)
            ok_(isinstance(result, AttrDict))
            eq_(result, expected)

        self.check_file_cache(path, check)
        eq_(gramex.cache.open(path), gramex.cache.open(path, 'yaml'))

    def test_open_template(self):
        path = os.path.join(cache_folder, 'template.txt')

        def check(reload):
            result, reloaded = gramex.cache.open(
                path, 'template', _reload_status=True, autoescape=None)
            eq_(reloaded, reload)
            ok_(isinstance(result, Template))
            first_line = result.generate(name='高').decode('utf-8').split('\n')[0]
            eq_(first_line, '1: name=高')

        self.check_file_cache(path, check)

    def test_open_markdown(self):
        path = os.path.join(cache_folder, 'markdown.md')
        extensions = [
            'markdown.extensions.codehilite',
            'markdown.extensions.extra',
            'markdown.extensions.toc',
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
        eq_(gramex.cache.open(path), gramex.cache.open(path, 'md'))

    def test_open_xml(self):
        path = os.path.join(cache_folder, 'data.svg')
        expected = etree.parse(path)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'svg', _reload_status=True)
            eq_(reloaded, reload)
            eq_(etree.tostring(result), etree.tostring(expected))

        self.check_file_cache(path, check)
        for ext in ['xml', 'svg', 'rss', 'atom']:
            eq_(etree.tostring(gramex.cache.open(path)),
                etree.tostring(gramex.cache.open(path, ext)))

    def test_open_custom(self):
        def img_size(path, scale=1):
            return tuple(v * scale for v in Image.open(path).size)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'png', _reload_status=True)
            eq_(reloaded, reload)
            eq_(result, expected)

        from PIL import Image
        path = os.path.join(cache_folder, 'data.png')
        expected = img_size(path)

        gramex.cache.open_callback['png'] = img_size
        self.check_file_cache(path, check)
        eq_(gramex.cache.open(path, scale=2), tuple(v * 2 for v in expected))

    def test_save(self):
        path = os.path.join(cache_folder, 'data.csv')
        data = pd.read_csv(path, encoding='utf-8')
        config = {
            'csv': dict(index=False, ignore_keyword=1),
            'xlsx': dict(index=False, sheet_name='Sheet1', ignore_keyword=1),
            'html': dict(index=False, escape=False, ignore_keyword=1),
            'hdf': dict(index=False, key='data', format='fixed', ignore_keyword=1),
            'json': dict(orient='records', ignore_keyword=1),
            # 'stata': dict(index=False),   # cannot test since it doesn't support unicode
        }
        for ext, kwargs in config.items():
            target = os.path.join(cache_folder, 'killme.' + ext)
            gramex.cache.save(data, target, **kwargs)
            try:
                result = gramex.cache.open(target)
                if ext == 'html':
                    result = result[0]
                elif ext == 'json':
                    result = pd.DataFrame(data)
                afe(result, data)
            finally:
                os.remove(target)

    def test_custom_cache(self):
        path = os.path.join(cache_folder, 'data.csv')
        cache = {}
        kwargs = {'_reload_status': True, '_cache': cache}
        result, reloaded = gramex.cache.open(path, 'csv', **kwargs)
        cache_key = (path, 'csv', hashfn(None), frozenset())
        self.assertIn(cache_key, cache)

        # Initially, the file is loaded
        eq_(reloaded, True)

        # Next time, it's loaded from the cache
        result, reloaded = gramex.cache.open(path, 'csv', **kwargs)
        eq_(reloaded, False)

        # If the cache is deleted, it reloads
        del cache[cache_key]
        result, reloaded = gramex.cache.open(path, 'csv', **kwargs)
        eq_(reloaded, True)

        # Additional kwargs are part of the cache key
        result, reloaded = gramex.cache.open(path, encoding='utf-8', **kwargs)
        cache_key = (path, None, hashfn(None), frozenset([('encoding', 'utf-8')]))
        self.assertIn(cache_key, cache)
        eq_(reloaded, True)
        result, reloaded = gramex.cache.open(path, encoding='utf-8', **kwargs)
        eq_(reloaded, False)

        # Changing the kwargs reloads the data
        result, reloaded = gramex.cache.open(path, encoding='cp1252', **kwargs)
        eq_(reloaded, True)
        result, reloaded = gramex.cache.open(path, encoding='cp1252', **kwargs)
        eq_(reloaded, False)

        # Cache is not fazed by non-hashable inputs.
        result, reloaded = gramex.cache.open(
            path,
            header=0,
            parse_dates={'date': [0, 1, 2]},
            dtype={'a': int, 'b': float, 'c': int},
            **kwargs)
        cache_key = (path, None, hashfn(None), frozenset([
            ('header', 0),                              # hashable values hashed as-is
            ('parse_dates', '{"date":[0,1,2]}'),        # converts to compact json if possible
            ('dtype', None),                            # gives up with None otherwise
        ]))
        self.assertIn(cache_key, cache)

    def test_change_cache(self):
        # gramex.cache.set_cache() changes the default cache
        path = os.path.join(cache_folder, 'data.csv')
        new_cache = {}
        old_cache = gramex.cache._OPEN_CACHE
        cache_key = (path, 'csv', hashfn(None), frozenset())

        # Ensure that the path is cached
        gramex.cache.open(path, 'csv')
        self.assertIn(cache_key, old_cache)
        old_cache_data = dict(old_cache)

        # Updating the cache copies data and empties from the old one
        gramex.cache._OPEN_CACHE = gramex.cache.set_cache(new_cache, old_cache)
        eq_(new_cache, old_cache_data)
        eq_(old_cache, {})

        # New requests are cached in the new cache
        result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True)
        eq_(reloaded, False)
        self.assertIn(cache_key, new_cache)
        del new_cache[cache_key]
        old_cache.pop(cache_key, None)
        self.assertNotIn(cache_key, new_cache)
        result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True)
        eq_(reloaded, True)
        self.assertIn(cache_key, new_cache)
        self.assertNotIn(cache_key, old_cache)

    def test_multiple_loaders(self):
        # Loading the same file via different callbacks should return different results
        path = os.path.join(cache_folder, 'multiformat.csv')
        data = gramex.cache.open(path, 'csv')
        ok_(isinstance(data, pd.DataFrame))
        text = gramex.cache.open(path, 'text')
        ok_(isinstance(text, string_types))
        none = gramex.cache.open(path, lambda path: None)
        ok_(none is None)

    def test_invalid_callbacks(self):
        path = os.path.join(cache_folder, 'multiformat.csv')
        with assert_raises(TypeError):
            gramex.cache.open(path, 'nonexistent')
        with assert_raises(TypeError):
            gramex.cache.open(path, 1)
        with assert_raises(TypeError):
            gramex.cache.open('invalid.ext')

    def test_stat(self):
        path = os.path.join(cache_folder, 'multiformat.csv')
        stat = os.stat(path)
        eq_(gramex.cache.stat(path), (stat.st_mtime, stat.st_size))
        eq_(gramex.cache.stat('nonexistent'), (None, None))

    def test_transform(self):
        # Check that transform function is applied and used as a cache key
        cache = {}
        path = os.path.join(cache_folder, 'data.csv')

        data = gramex.cache.open(path, 'csv', transform=len, _cache=cache)
        eq_(data, len(pd.read_csv(path)))                   # noqa - ignore encoding
        cache_key = (path, 'csv', hashfn(len), frozenset([]))
        self.assertIn(cache_key, cache)

        def transform2(d):
            return d['a'].sum()

        data = gramex.cache.open(path, 'csv', transform=transform2, _cache=cache)
        eq_(data, pd.read_csv(path)['a'].sum())             # noqa - ignore encoding
        cache_key = (path, 'csv', hashfn(transform2), frozenset([]))
        self.assertIn(cache_key, cache)

        # Check that non-callable transforms are ignored but used as cache key
        data = gramex.cache.open(path, 'csv', transform='ignore', _cache=cache)
        afe(data, pd.read_csv(path))         # noqa - ignore encoding
        cache_key = (path, 'csv', hashfn('ignore'), frozenset([]))
        self.assertIn(cache_key, cache)

        # Check that temporary caches are hashed by function
        v = 1
        data = gramex.cache.open(path, 'csv', lambda x: v, _cache=cache)
        eq_(data, 1)
        v = 2
        data = gramex.cache.open(path, 'csv', lambda x: v, _cache=cache)
        eq_(data, 2)


class TestSqliteCacheQuery(unittest.TestCase):
    data = pd.read_csv(os.path.join(cache_folder, 'data.csv'), encoding='utf-8')
    states = [['t1'], 'SELECT COUNT(*) FROM t1', lambda: gramex.cache.stat(state_file)]

    @classmethod
    def setUpClass(cls):
        cls.url = dbutils.sqlite_create_db('test_cache.db', t1=cls.data, t2=cls.data)
        cls.engine = sa.create_engine(cls.url, encoding=str_utf8)

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
        kwargs = dict(sql=sql, engine=self.engine, state=['t1'], _reload_status=True)
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
            kwargs = dict(sql=sql, engine=self.engine, state=state, _reload_status=True)
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
        cls.url = dbutils.mysql_create_db(variables.MYSQL_SERVER, 'test_cache',
                                          t1=cls.data, t2=cls.data)
        cls.engine = sa.create_engine(cls.url, encoding=str_utf8)

    @classmethod
    def tearDownClass(cls):
        dbutils.mysql_drop_db(variables.MYSQL_SERVER, 'test_cache')


class TestPostgresCacheQuery(TestSqliteCacheQuery):
    states = ['SELECT COUNT(*) FROM t1', lambda: gramex.cache.stat(state_file)]

    @classmethod
    def setUpClass(cls):
        cls.url = dbutils.postgres_create_db(variables.POSTGRES_SERVER, 'test_cache',
                                             **{'t1': cls.data, 't2': cls.data, 'sc.t3': cls.data})
        cls.engine = sa.create_engine(cls.url, encoding=str_utf8)

    def test_schema(self):
        afe(
            gramex.cache.query('SELECT * FROM sc.t3', engine=self.engine), self.data)

    @classmethod
    def tearDownClass(cls):
        dbutils.postgres_drop_db(variables.POSTGRES_SERVER, 'test_cache')


def wait(future):
    wait_till(future.done)
    return future.result()


def wait_till(condition):
    while not condition():
        time.sleep(small_delay)


class TestSubprocess(unittest.TestCase):
    args = ['python', os.path.join(folder, 'subprocess_check.py')]          # Instant result
    args1 = ['python', os.path.join(folder, 'subprocess_check.py'), '1']    # Result after delay
    hello = ['python', '-c', 'print("hello")']

    @staticmethod
    def msg(s):
        '''Returns the string + newline as UTF-8 bytestring'''
        return (s + os.linesep).encode('utf-8')

    def test_stream_none(self):
        proc = gramex.cache.Subprocess(self.args)
        stdout, stderr = [wait(future) for future in proc.wait_for_exit()]
        eq_(stdout, self.msg('OUT:0'))
        eq_(stderr, self.msg('ERR:0'))

        proc = gramex.cache.Subprocess(self.args1)
        stdout, stderr = [wait(future) for future in proc.wait_for_exit()]
        eq_(stdout, self.msg('OUT:0') + self.msg('OUT:1'))
        eq_(stderr, self.msg('ERR:0') + self.msg('ERR:1'))

    def test_stream_list(self):
        proc = gramex.cache.Subprocess(
            self.args, stream_stdout='list_out', stream_stderr='list_err', buffer_size='line')
        [wait(future) for future in proc.wait_for_exit()]
        eq_(proc.list_out, [self.msg('OUT:0')])
        eq_(proc.list_err, [self.msg('ERR:0')])

        proc = gramex.cache.Subprocess(
            self.args1, stream_stdout='list_out', stream_stderr='list_err', buffer_size='line')
        wait_till(lambda: len(proc.list_out) > 0)
        wait_till(lambda: len(proc.list_err) > 0)
        eq_(proc.list_out, [self.msg('OUT:0')])
        eq_(proc.list_err, [self.msg('ERR:0')])
        wait_till(lambda: len(proc.list_out) > 1)
        wait_till(lambda: len(proc.list_err) > 1)
        eq_(proc.list_out, [self.msg('OUT:0'), self.msg('OUT:1')])
        eq_(proc.list_err, [self.msg('ERR:0'), self.msg('ERR:1')])
        [wait(future) for future in proc.wait_for_exit()]
        eq_(proc.list_out, [self.msg('OUT:0'), self.msg('OUT:1')])
        eq_(proc.list_err, [self.msg('ERR:0'), self.msg('ERR:1')])

    def test_stream_queue(self):
        proc = gramex.cache.Subprocess(
            self.args, stream_stdout='queue_out', stream_stderr='queue_err')
        [wait(future) for future in proc.wait_for_exit()]
        eq_(proc.queue_out.get(), self.msg('OUT:0'))
        eq_(proc.queue_err.get(), self.msg('ERR:0'))

        proc = gramex.cache.Subprocess(
            self.args1, stream_stdout='queue_out', stream_stderr='queue_err', buffer_size='line')
        eq_(proc.queue_out.get(), self.msg('OUT:0'))
        eq_(proc.queue_err.get(), self.msg('ERR:0'))
        eq_(proc.queue_out.get(), self.msg('OUT:1'))
        eq_(proc.queue_err.get(), self.msg('ERR:1'))
        [wait(future) for future in proc.wait_for_exit()]
        eq_(proc.queue_out.qsize(), 0)
        eq_(proc.queue_err.qsize(), 0)

    def test_stream_blend(self):
        proc = gramex.cache.Subprocess(
            self.args1, stream_stdout='list_out', stream_stderr='list_out', buffer_size='line')
        [wait(future) for future in proc.wait_for_exit()]
        eq_(set(proc.list_out), {self.msg(s) for s in ('OUT:0', 'OUT:1', 'ERR:0', 'ERR:1')})

        proc = gramex.cache.Subprocess(
            self.args1, stream_stdout='queue_out', stream_stderr='queue_out', buffer_size='line')
        [wait(future) for future in proc.wait_for_exit()]
        items = set()
        for index in range(proc.queue_out.qsize()):
            items.add(proc.queue_out.get_nowait())
        eq_(items, {self.msg(s) for s in ('OUT:0', 'OUT:1', 'ERR:0', 'ERR:1')})

    def test_daemon_reuse(self):
        procs = [
            wait(gramex.cache.daemon(self.args)),
            wait(gramex.cache.daemon(self.args)),
            wait(gramex.cache.daemon(self.args1)),
        ]
        eq_(procs[0].proc.pid, procs[1].proc.pid)
        ok_(procs[0].proc.pid != procs[2].proc.pid)
        for proc in procs:
            [wait(future) for future in proc.wait_for_exit()]

    def test_daemon_stream(self):
        out = []
        proc = wait(gramex.cache.daemon(self.args, stream=out.append))
        [wait(future) for future in proc.wait_for_exit()]
        eq_(set(out), {self.msg('OUT:0'), self.msg('ERR:0')})

    def test_daemon_first_line(self):
        # Streaming output is still possible
        out = []
        proc = wait(gramex.cache.daemon(self.hello, first_line='hello', stream=out.append))
        [wait(future) for future in proc.wait_for_exit()]
        eq_(set(out), {self.msg('hello')})

        # Incorrect first line raises an error
        with assert_raises(AssertionError):
            proc = wait(gramex.cache.daemon(self.args, first_line='NOTHING'))
        [wait(future) for future in proc.wait_for_exit()]

        # Correct first line can be a string or regex
        proc = wait(gramex.cache.daemon(self.hello, first_line='hello'))
        [wait(future) for future in proc.wait_for_exit()]
        proc = wait(gramex.cache.daemon(self.args, first_line=re.compile(r'(OUT|ERR):\d\s*')))
        [wait(future) for future in proc.wait_for_exit()]


def tearDownModule():
    if os.path.exists(state_file):
        os.unlink(state_file)
