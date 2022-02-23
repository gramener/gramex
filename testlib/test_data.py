import io
import os
import json
import shutil
import unittest
import gramex.data
import gramex.cache
import numpy as np
import pandas as pd
import pymongo.errors
import sqlalchemy as sa
from orderedattrdict import AttrDict
from nose.plugins.skip import SkipTest
from nose.tools import eq_, ok_, assert_raises
from . import folder, sales_file, remove_if_possible, dbutils, afe, ase

server = AttrDict(
    mysql=os.environ.get('MYSQL_SERVER', 'localhost'),
    postgres=os.environ.get('POSTGRES_SERVER', 'localhost'),
    mongodb=os.environ.get('MONGODB_SERVER', 'localhost')
)


def eqframe(actual, expected, **kwargs):
    '''Same as assert_frame_equal or afe, but does not compare index'''
    expected.index = actual.index
    afe(actual, expected, **kwargs)


class TestFilter(unittest.TestCase):
    sales = gramex.cache.open(sales_file, 'xlsx')
    dates = gramex.cache.open(sales_file, 'xlsx', sheet_name='dates')
    db = set()

    def test_get_engine(self):
        check = gramex.data.get_engine
        eq_(check(pd.DataFrame()), 'dataframe')
        eq_(check('dir:///d:/temp/data.txt'), 'dir')
        eq_(check('dir:////root/path'), 'dir')
        eq_(check('file:///d:/temp/data.txt'), 'file')
        eq_(check('file:////root/path'), 'file')
        sqlalchemy_urls = [
            'postgresql://scott:tiger@localhost:5432/mydatabase',
            'mysql://scott:tiger@localhost/foo',
            'oracle://scott:tiger@127.0.0.1:1521/sidname',
            'sqlite:///foo.db',
        ]
        for url in sqlalchemy_urls:
            eq_(check(url), 'sqlalchemy')
        eq_(check(folder), 'dir')
        eq_(check(os.path.join(folder, 'test_data.py')), 'file')
        eq_(check('/root/nonexistent/'), 'file')
        eq_(check('/root/nonexistent.txt'), 'file')

    def test_filter_col(self):
        cols = ['sales', 'growth', 'special ~!@#$%^&*()_+[]\\{}|;\':",./<>?高']
        for col in cols:
            for op in [''] + gramex.data.operators:
                eq_(gramex.data._filter_col(col + op, cols), (col, None, op))
                for agg in ['SUM', 'min', 'Max', 'AVG', 'AnYthiNG']:
                    eq_(gramex.data._filter_col(col + '|' + agg + op, cols), (col, agg, op))

    def test_dirstat(self):
        for name in ('test_cache', 'test_config', '.'):
            path = os.path.normpath(os.path.join(folder, name))
            files = sum((dirs + files for root, dirs, files in os.walk(path)), [])
            result = gramex.data.dirstat(path)
            eq_(len(files), len(result))
            eq_({'path', 'name', 'dir', 'type', 'size', 'mtime', 'level'}, set(result.columns))
            ase(result['path'], path + result['dir'].str.replace('/', os.sep) + result['name'],
                check_names=False)

    def flatten_sort(self, expected, by, sum_na, *columns):
        expected.columns = columns
        expected.reset_index(inplace=True)
        if sum_na:
            for col in columns:
                if col.lower().endswith('|sum'):
                    expected[col].replace({0.0: np.nan}, inplace=True)
        expected.sort_values(by, inplace=True)

    def check_filter(self, df=None, na_position='last', sum_na=False, **kwargs):
        '''
        Tests a filter method. The filter method filters the sales dataset using
        an "args" dict as argument. This is used to test filter with frame, file
        and sqlalchemy URLs

        - ``na_position`` indicates whether NA are moved to the end or not. Can
          be 'first' or 'last'
        - ``sum_na`` indicates whether SUM() over zero elements results in NA
          (instead of 0)
        '''
        def eq(args, expected, **eqkwargs):
            meta = {}
            actual = gramex.data.filter(meta=meta, args=args, **kwargs)
            eqframe(actual, expected, **eqkwargs)
            return meta

        sales = self.sales if df is None else df

        meta = eq({}, sales)
        eq_(meta['filters'], [])
        eq_(meta['ignored'], [])
        eq_(meta['sort'], [])
        eq_(meta['offset'], 0)
        eq_(meta['limit'], None)

        m = eq({'देश': ['भारत']},
               sales[sales['देश'] == 'भारत'])
        eq_(m['filters'], [('देश', '', ('भारत',))])

        m = eq({'city': ['Hyderabad', 'Coimbatore']},
               sales[sales['city'].isin(['Hyderabad', 'Coimbatore'])])
        eq_(m['filters'], [('city', '', ('Hyderabad', 'Coimbatore'))])

        # ?col= is treated as non-null col values
        m = eq({'sales': []}, sales[pd.notnull(sales['sales'])])
        eq_(m['filters'], [('sales', '', ())])
        m = eq({'sales': ['']}, sales[pd.notnull(sales['sales'])])
        eq_(m['filters'], [('sales', '', ())])

        # ?col!= is treated as null col values
        # Don't check dtype. Database may return NULL as an object, not float
        m = eq({'sales!': []}, sales[pd.isnull(sales['sales'])], check_dtype=False)
        eq_(m['filters'], [('sales', '!', ())])
        m = eq({'sales!': ['']}, sales[pd.isnull(sales['sales'])], check_dtype=False)
        eq_(m['filters'], [('sales', '!', ())])

        m = eq({'product!': ['Biscuit', 'Crème']},
               sales[~sales['product'].isin(['Biscuit', 'Crème'])])
        eq_(m['filters'], [('product', '!', ('Biscuit', 'Crème'))])

        m = eq({'city>': ['Bangalore'], 'city<': ['Singapore']},
               sales[(sales['city'] > 'Bangalore') & (sales['city'] < 'Singapore')])
        eq_(set(m['filters']), {('city', '>', ('Bangalore',)), ('city', '<', ('Singapore',))})

        # Ignore empty columns
        m = eq({'city': ['Hyderabad', 'Coimbatore', ''], 'c1': [''], 'c2>': [''], 'city~': ['']},
               sales[sales['city'].isin(['Hyderabad', 'Coimbatore'])])

        m = eq({'city>~': ['Bangalore'], 'city<~': ['Singapore']},
               sales[(sales['city'] >= 'Bangalore') & (sales['city'] <= 'Singapore')])
        eq_(set(m['filters']), {('city', '>~', ('Bangalore',)), ('city', '<~', ('Singapore',))})

        m = eq({'city~': ['ore']},
               sales[sales['city'].str.contains('ore')])
        eq_(m['filters'], [('city', '~', ('ore',))])

        m = eq({'product': ['Biscuit'], 'city': ['Bangalore'], 'देश': ['भारत']},
               sales[(sales['product'] == 'Biscuit') & (sales['city'] == 'Bangalore') &
                     (sales['देश'] == 'भारत')])
        eq_(set(m['filters']), {('product', '', ('Biscuit',)), ('city', '', ('Bangalore',)),
                                ('देश', '', ('भारत',))})

        m = eq({'city!~': ['ore']},
               sales[~sales['city'].str.contains('ore')])
        eq_(m['filters'], [('city', '!~', ('ore',))])

        m = eq({'sales>': ['100'], 'sales<': ['1000']},
               sales[(sales['sales'] > 100) & (sales['sales'] < 1000)])
        eq_(set(m['filters']), {('sales', '>', (100,)), ('sales', '<', (1000,))})

        m = eq({'growth<': [0.5]},
               sales[sales['growth'] < 0.5])

        m = eq({'sales>': ['100'], 'sales<': ['1000'], 'growth<': ['0.5']},
               sales[(sales['sales'] > 100) & (sales['sales'] < 1000) & (sales['growth'] < 0.5)])

        m = eq({'देश': ['भारत'], '_sort': ['sales']},
               sales[sales['देश'] == 'भारत'].sort_values('sales', na_position=na_position))
        eq_(m['sort'], [('sales', True)])

        m = eq({'product<~': ['Biscuit'], '_sort': ['-देश', '-growth']},
               sales[sales['product'] == 'Biscuit'].sort_values(
                    ['देश', 'growth'], ascending=[False, False], na_position=na_position))
        eq_(m['filters'], [('product', '<~', ('Biscuit',))])
        eq_(m['sort'], [('देश', False), ('growth', False)])

        m = eq({'देश': ['भारत'], '_offset': ['4'], '_limit': ['8']},
               sales[sales['देश'] == 'भारत'].iloc[4:12])
        eq_(m['filters'], [('देश', '', ('भारत',))])
        eq_(m['offset'], 4)
        eq_(m['limit'], 8)

        cols = ['product', 'city', 'sales']
        m = eq({'देश': ['भारत'], '_c': cols},
               sales[sales['देश'] == 'भारत'][cols])
        eq_(m['filters'], [('देश', '', ('भारत',))])

        ignore_cols = ['product', 'city']
        m = eq({'देश': ['भारत'], '_c': ['-' + c for c in ignore_cols]},
               sales[sales['देश'] == 'भारत'][[c for c in sales.columns if c not in ignore_cols]])
        eq_(m['filters'], [('देश', '', ('भारत',))])

        # Non-existent column does not raise an error for any operation
        for op in ['', '~', '!', '>', '<', '<~', '>', '>~']:
            m = eq({'nonexistent' + op: ['']}, sales)
            eq_(m['ignored'], [('nonexistent' + op, [''])])
        # Non-existent sorts do not raise an error
        m = eq({'_sort': ['nonexistent', 'sales']},
               sales.sort_values('sales', na_position=na_position))
        eq_(m['ignored'], [('_sort', ['nonexistent'])])
        eq_(m['sort'], [('sales', True)])

        # Non-existent _c does not raise an error
        m = eq({'_c': ['nonexistent', 'sales']}, sales[['sales']])
        eq_(m['ignored'], [('_c', ['nonexistent'])])

        for by in [['देश'], ['देश', 'city', 'product']]:
            # _by= groups by column(s) and sums all numeric columns
            # and ignores non-existing columns
            expected = sales.groupby(by).agg(AttrDict([
                ['sales', 'sum'],
                ['growth', 'sum'],
            ]))
            self.flatten_sort(expected, by, sum_na, 'sales|sum', 'growth|sum')
            m = eq({'_by': by + ['na'], '_sort': by}, expected)
            eq_(m['by'], by)
            eq_(m['ignored'], [('_by', 'na')])

            # _by allows custom aggregation
            aggs = [
                'city|count',
                'product|MAX', 'product|MIN',
                'sales|count', 'sales|SUM',
                'growth|sum', 'growth|AvG',
            ]
            agg_pd = AttrDict([
                ['city', 'count'],
                ['product', ['max', 'min']],
                ['sales', ['count', 'sum']],
                ['growth', ['sum', 'mean']],
            ])
            expected = sales.groupby(by).agg(agg_pd)
            self.flatten_sort(expected, by, sum_na, *aggs)
            eq({'_by': by, '_sort': by, '_c': aggs}, expected)

            # _by with HAVING as well as WHERE filters
            filters = [
                (None, (None, None)),
                ('city == "Singapore"', ('city', 'Singapore')),
                ('sales > 100', ('sales>', '100')),
            ]
            for query, (key, val) in filters:
                # Filter by city. Then group by product and aggregate by sales & growth
                filtered = sales if query is None else sales.query(query)
                expected = filtered.groupby(by).agg(agg_pd)
                self.flatten_sort(expected, by, sum_na, *aggs)
                # Make sure there's enough data. Sometimes, I goof up above above
                # and pick a scenario that return no data in the first place.
                ok_(len(expected) > 0)
                for having in aggs:
                    # Apply HAVING at the mid-point of aggregated data.
                    # Cannot use .median() since data may not be numeric.
                    midpoint = expected[having].sort_values().iloc[len(expected) // 2]
                    # Floating point bugs surface unless we round it off.
                    # In Pandas 1.x, we need a small additional buffer.
                    if isinstance(midpoint, float):
                        buffer = 0.001
                        midpoint = round(midpoint, 2) + buffer
                    subset = expected[expected[having] > midpoint]
                    args = {'_by': by, '_sort': by, '_c': aggs,
                            having + '>': [str(midpoint)]}
                    if query is not None:
                        args[key] = [val]
                    # When subset is empty, the SQL returned types may not match.
                    # Don't check_dtype in that case.
                    eq(args, subset, check_dtype=len(subset) > 0)

        # _by= empty
        aggs = ['growth|sum', 'sales|sum']
        expected = pd.DataFrame(
            [[sales[agg[0]].agg(agg[1]) for agg in [x.split('|') for x in aggs]]],
            columns=aggs
        )
        eq({'_by': [], '_c': aggs}, expected)
        expected = (sales.select_dtypes(include=np.number).agg('sum')
                    .to_frame().T.add_suffix('|sum'))
        eq({'_by': []}, expected)
        for _c in [[], ['']]:
            ok_(gramex.data.filter(args={'_by': [], '_c': _c}, **kwargs).empty)

        # Invalid values raise errors
        with assert_raises(ValueError):
            eq({'_limit': ['abc']}, sales)
        with assert_raises(ValueError):
            eq({'_offset': ['abc']}, sales)

    def test_frame(self):
        self.check_filter(url=self.sales)

    def test_file(self):
        self.check_filter(url=sales_file)
        afe(
            gramex.data.filter(url=sales_file, transform='2.1', sheet_name='dummy'),
            gramex.cache.open(sales_file, 'excel', transform='2.2', sheet_name='dummy'),
        )
        self.check_filter(
            url=sales_file,
            transform=lambda d: d[d['sales'] > 100],
            df=self.sales[self.sales['sales'] > 100],
        )
        with assert_raises(ValueError):
            gramex.data.filter(url='', engine='nonexistent')
        with assert_raises(OSError):
            gramex.data.filter(url='nonexistent')
        with assert_raises(TypeError):
            gramex.data.filter(url=os.path.join(folder, 'test_cache_module.py'))

    def check_filter_db(self, dbname, url, na_position, sum_na=True):
        self.db.add(dbname)
        df = self.sales[self.sales['sales'] > 100]
        kwargs = {'na_position': na_position, 'sum_na': sum_na}
        self.check_filter(url=url, table='sales', **kwargs)
        self.check_filter(url=url, table='sales',
                          transform=lambda d: d[d['sales'] > 100], df=df, **kwargs)
        self.check_filter(url=url, table='sales',
                          query='SELECT * FROM sales WHERE sales > 100', df=df, **kwargs)
        self.check_filter(url=url, table='sales',
                          query='SELECT * FROM sales WHERE sales > 999999',
                          queryfile=os.path.join(folder, 'sales-query.sql'), df=df, **kwargs)
        self.check_filter(url=url, table=['sales', 'sales'],
                          query='SELECT * FROM sales WHERE sales > 100',
                          transform=lambda d: d[d['growth'] < 0.5],
                          df=df[df['growth'] < 0.5], **kwargs)
        self.check_filter(url=url,
                          query='SELECT * FROM sales WHERE sales > 100',
                          transform=lambda d: d[d['growth'] < 0.5],
                          df=df[df['growth'] < 0.5], **kwargs)
        self.check_filter(url=url, table='sales',
                          query='SELECT * FROM sales WHERE sales > 100',
                          transform=lambda d: d[d['growth'] < 0.5],
                          df=df[df['growth'] < 0.5], **kwargs)
        # Check both parameter substitutions -- {} formatting and : substitution
        afe(gramex.data.filter(url=url, table='{x}', args={'x': ['sales']}), self.sales)
        actual = gramex.data.filter(
            url=url, table='{兴}', args={
                '兴': ['sales'],
                'col': ['growth'],
                'val': [0],
                'city': ['South Plainfield'],
            },
            query='SELECT * FROM {兴} WHERE {col} > :val AND city = :city',
        )
        expected = self.sales[(self.sales['growth'] > 0) &
                              (self.sales['city'] == 'South Plainfield')]
        eqframe(actual, expected)

        # _by= _sort= _c=agg(s)
        by = ['product']
        aggs = ['growth|sum', 'sales|sum']
        sort = ['sales|sum']
        expected = df.groupby(by).agg(AttrDict([agg.split('|') for agg in aggs]))
        self.flatten_sort(expected, sort, sum_na, *aggs)
        params = {'_by': by, '_c': aggs, '_sort': sort, 'sales>': [100]}
        actual = gramex.data.filter(url, table='sales', args=params)
        eqframe(actual, expected)

        # Test invalid parameters
        with assert_raises(ValueError):
            gramex.data.filter(url=url, table=1, query='SELECT * FROM sales WHERE sales > 100')
        with assert_raises(ValueError):
            gramex.data.filter(url=url, table={}, query='SELECT * FROM sales WHERE sales > 100')

        # Arguments with spaces raise an Exception
        with assert_raises(Exception):
            gramex.data.filter(url=url, table='{x}', args={'x': ['a b']})
        with assert_raises(Exception):
            gramex.data.filter(url=url, table='{x}', args={'x': ['sales'], 'p': ['a b']},
                               query='SELECT * FROM {x} WHERE {p} > 0')

    def check_filter_dates(self, dbname, url):
        self.db.add(dbname)
        df = self.dates[self.dates['date'] > '2018-02-01 01:00:00']
        dff = gramex.data.filter(url=url, table='dates', args={'date>': ['2018-02-01 01:00:00']})
        eqframe(dff, df)

    def test_mysql(self):
        url = dbutils.mysql_create_db(server.mysql, 'test_filter', **{
            'sales': self.sales, 'dates': self.dates})
        self.check_filter_db('mysql', url, na_position='first')
        self.check_filter_dates('mysql', url)

    def test_postgres(self):
        url = dbutils.postgres_create_db(server.postgres, 'test_filter', **{
            'sales': self.sales, 'filter.sales': self.sales, 'dates': self.dates})
        self.check_filter_db('postgres', url, na_position='last')
        self.check_filter(url=url, table='filter.sales', na_position='last', sum_na=True)
        self.check_filter_dates('postgres', url)

    def test_sqlite(self):
        url = dbutils.sqlite_create_db('test_filter.db', **{
            'sales': self.sales, 'dates': self.dates})
        self.check_filter_db('sqlite', url, na_position='first')
        self.check_filter_dates('sqlite', url)

    def test_mongodb(self):
        url = f'mongodb://{server.mongodb}'
        db = 'test_filter'
        try:
            dbutils.mongodb_create_db(url, db, **{'sales': self.sales, 'empty': pd.DataFrame()})
        except pymongo.errors.ServerSelectionTimeoutError:
            raise SkipTest(f'MongoDB not set up at {server.mongodb}')
        self.db.add('mongodb')
        kwargs = {
            'url': url,
            'collection': 'sales',
            'database': db,
        }

        def size(b=0, **qwargs):
            eq_(len(gramex.data.filter(**qwargs, **kwargs)), b=b)

        size(args={'sales<': ['100']}, b=11)
        size(args={'growth>': ['0.1']}, b=5)
        size(args={'city': ['Coimbatore']}, b=4)
        size(args={'देश': ['भारत', 'Singapore']}, b=16)
        size(args={'product!': ['Biscuit']}, b=18)
        size(args={'sales!': ['26.4', '94.4']}, b=22)
        size(args={'sales>~': ['200']}, b=8)
        size(args={'sales<~': ['41.9']}, b=8)
        size(args={'city~': ['South']}, b=4)
        size(args={'city!~': ['Newport']}, b=20)
        size(args={'sales>': ['20'], 'sales<': ['500']}, b=13)
        size(args={'city~': ['South'], 'product': ['Biscuit']}, b=1)
        # TODO: NOT NULL
        # size(args={'sales!': []}, b=2)
        # size(args={'sales': []}, b=22)

        size(query={'sales': {'$lt': 100}}, b=11)
        size(query={'देश': {'$in': ['भारत', 'Singapore']}}, b=16)
        size(query={'देश': {'$in': ['भारत', '{country}']}}, args={'country': ['Singapore']}, b=16)

        size(args={'sales<': ['100'], 'missing': ['ignored']}, b=11)

        kwargs['collection'] = 'empty'
        size(args={}, b=0)
        size(args={'missing': ['ignored']}, b=0)

    @classmethod
    def tearDownClass(cls):
        if 'mysql' in cls.db:
            dbutils.mysql_drop_db(server.mysql, 'test_filter')
        if 'postgres' in cls.db:
            dbutils.postgres_drop_db(server.postgres, 'test_filter')
        if 'sqlite' in cls.db:
            dbutils.sqlite_drop_db('test_filter.db')
        if 'mongodb' in cls.db:
            dbutils.mongodb_drop_db(f'mongodb://{server.mongodb}', 'test_filter')


class TestInsert(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.insert_file = sales_file + '.insert.xlsx'
        shutil.copy(sales_file, cls.insert_file)
        cls.tmpfiles = [cls.insert_file]
        cls.insert_rows = {
            'देश': ['भारत', None],
            'city': [None, 'Paris'],
            'product': ['芯片', 'Crème'],
            'sales': ['0', -100],
            # Do not add growth column, to see if it inserts defaults
        }
        cls.db = set()

    def test_insert_frame(self):
        raise SkipTest('TODO: write insert test cases for DataFrame')

    def test_insert_file(self):
        data = gramex.cache.open(self.insert_file, 'xlsx')
        gramex.data.insert(url=self.insert_file, args=self.insert_rows)
        new_data = gramex.cache.open(self.insert_file, 'xlsx')
        # Check original data is identical
        afe(data, new_data.head(len(data)))
        # Check if added rows are correct
        added_rows = pd.DataFrame(self.insert_rows)
        added_rows['sales'] = added_rows['sales'].astype(float)
        added_rows['growth'] = np.nan
        added_rows.index = new_data.tail(2).index
        afe(new_data.tail(2), added_rows, check_like=True)

    def test_insert_new_file(self):
        new_files = [
            {'url': os.path.join(folder, 'insert.csv'), 'encoding': 'utf-8'},
            {'url': os.path.join(folder, 'insert.xlsx'), 'sheet_name': 'test'},
            {'url': os.path.join(folder, 'insert.hdf'), 'key': 'test'},
        ]
        for conf in new_files:
            remove_if_possible(conf['url'])
            self.tmpfiles.append(conf['url'])
            gramex.data.insert(args=self.insert_rows, **conf)
            # Check if added rows are correct
            try:
                actual = gramex.data.filter(**conf)
            except ValueError:
                # TODO: This is a temporary fix for NumPy 1.16.2, Tables 3.4.4
                # https://github.com/pandas-dev/pandas/issues/24839
                if conf['url'].endswith('.hdf') and np.__version__.startswith('1.16'):
                    raise SkipTest('Ignore NumPy 1.16.2 / PyTables 3.4.4 quirk')
            else:
                expected = pd.DataFrame(self.insert_rows)
                actual['sales'] = actual['sales'].astype(float)
                expected['sales'] = expected['sales'].astype(float)
                afe(actual, expected, check_like=True)

    def test_insert_mysql(self):
        url = dbutils.mysql_create_db(server.mysql, 'test_insert')
        self.check_insert_db(url, 'mysql')

    def test_insert_postgres(self):
        url = dbutils.postgres_create_db(server.postgres, 'test_insert')
        self.check_insert_db(url, 'postgres')

    def test_insert_sqlite(self):
        url = dbutils.sqlite_create_db('test_insert.db')
        self.check_insert_db(url, 'sqlite')

    def check_insert_db(self, url, dbname):
        self.db.add(dbname)

        # Insert 2 rows in the EMPTY database with a primary key
        rows = self.insert_rows.copy()
        rows['primary_key'] = [1, 2]
        meta = {}
        inserted = gramex.data.insert(url, meta, args=rows, table='test_insert', id='primary_key')
        eq_(inserted, 2, 'insert() returns # of records added')
        # metadata has no filters applied, and no columns ignored
        eq_(meta['filters'], [])
        eq_(meta['ignored'], [])
        # Actual data created has the same content, factoring in type conversion
        actual = gramex.data.filter(url, table='test_insert')
        expected = pd.DataFrame(rows)
        for df in [actual, expected]:
            df['sales'] = df['sales'].astype(float)
        afe(actual, expected, check_like=True)
        # Check if it created a primary key
        engine = sa.create_engine(url)
        insp = sa.inspect(engine)
        ok_('primary_key' in insp.get_pk_constraint('test_insert')['constrained_columns'])
        # Inserting duplicate keys raises an Exception
        with assert_raises(sa.exc.IntegrityError):
            gramex.data.insert(url, args=rows, table='test_insert', id='primary_key')

        # Inserting a single row returns meta['data']['inserted'] with the primary key
        rows = {'primary_key': [3], 'देश': ['भारत'], 'city': ['London'], 'sales': ['']}
        inserted = gramex.data.insert(url, meta, args=rows, table='test_insert', id='primary_key')
        eq_(inserted, 1, 'insert() returns # of records added')
        eq_(meta['inserted'], [{'primary_key': 3}])

        # Adding multiple primary keys via id= is supported
        rows = {'a': [1, 2], 'b': [True, False], 'x': [3, None], 'y': [None, 'y']}
        inserted = gramex.data.insert(url, meta, args=rows, table='t2', id=['a', 'b'])
        eq_(inserted, 2, 'insert() returns # of records added')
        eq_(insp.get_pk_constraint('t2')['constrained_columns'], ['a', 'b'],
            'multiple primary keys are created')
        # Multiple primary keys are returned
        rows = {'a': [3], 'b': [True]}
        inserted = gramex.data.insert(url, meta, args=rows, table='t2', id=['a', 'b'])
        eq_(meta['inserted'], [{'a': 3, 'b': True}])

        # Primary keys not specified in input (AUTO INCREMENT) are turned
        gramex.data.alter(url, 't3', columns={
            'id': {'type': 'int', 'primary_key': True, 'autoincrement': True},
            'x': 'varchar(10)'
        })
        # Single inserts return the ID
        gramex.data.insert(url, meta, args={'x': ['a']}, table='t3')
        eq_(meta['inserted'], [{'id': 1}])
        gramex.data.insert(url, meta, args={'x': ['b']}, table='t3')
        eq_(meta['inserted'], [{'id': 2}])
        # TODO: multiple inserts don't yet return the IDs. When that's done in SQLAlchemy 1.4,
        # implement test cases here.

    @classmethod
    def tearDownClass(cls):
        for path in cls.tmpfiles:
            remove_if_possible(path)
        if 'mysql' in cls.db:
            dbutils.mysql_drop_db(server.mysql, 'test_insert')
        if 'postgres' in cls.db:
            dbutils.postgres_drop_db(server.postgres, 'test_insert')
        if 'sqlite' in cls.db:
            dbutils.sqlite_drop_db('test_insert.db')


class TestEdit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.edit_file = sales_file + '.edit.xlsx'
        shutil.copy(sales_file, cls.edit_file)
        cls.tmpfiles = [cls.edit_file]

    def test_update(self):
        args = {
            'देश': ['भारत'],
            'city': ['Hyderabad'],
            'product': ['Crème'],
            'sales': ['0']
        }
        data = gramex.cache.open(self.edit_file, 'xlsx')
        types_original = data.dtypes
        gramex.data.update(data, args=args, id=['देश', 'city', 'product'])
        ase(types_original, data.dtypes)

    def test_delete(self):
        raise SkipTest('TODO: write delete test cases')

    @classmethod
    def tearDownClass(cls):
        for path in cls.tmpfiles:
            remove_if_possible(path)


class TestDownload(unittest.TestCase):
    @classmethod
    def setupClass(cls):
        cls.sales = gramex.cache.open(sales_file, 'xlsx')
        cls.dummy = pd.DataFrame({
            'खुश': ['高兴', 'سعيد'],
            'length': [1.2, None],
        })

    def test_download_csv(self):
        out = gramex.data.download(self.dummy, format='csv')
        ok_(out.startswith(''.encode('utf-8-sig')))
        afe(pd.read_csv(io.BytesIO(out), encoding='utf-8'), self.dummy)

        out = gramex.data.download(AttrDict([
            ('dummy', self.dummy),
            ('sales', self.sales),
        ]), format='csv')
        lines = out.splitlines(True)
        eq_(lines[0], 'dummy\n'.encode('utf-8-sig'))
        actual = pd.read_csv(io.BytesIO(b''.join(lines[1:4])), encoding='utf-8')
        afe(actual, self.dummy)

        eq_(lines[5], 'sales\n'.encode('utf-8'))
        actual = pd.read_csv(io.BytesIO(b''.join(lines[6:])), encoding='utf-8')
        afe(actual, self.sales)

    def test_download_json(self):
        out = gramex.data.download(self.dummy, format='json')
        afe(pd.read_json(io.BytesIO(out)), self.dummy, check_like=True)

        out = gramex.data.download({'dummy': self.dummy, 'sales': self.sales}, format='json')
        result = json.loads(out, object_pairs_hook=AttrDict)

        def from_json(key):
            s = json.dumps(result[key])
            # PY2 returns str (binary). PY3 returns str (unicode). Ensure it's binary
            if isinstance(s, str):
                s = s.encode('utf-8')
            return pd.read_json(io.BytesIO(s))

        afe(from_json('dummy'), self.dummy, check_like=True)
        afe(from_json('sales'), self.sales, check_like=True)

    def test_download_excel(self):
        out = gramex.data.download(self.dummy, format='xlsx')
        afe(pd.read_excel(io.BytesIO(out), engine='openpyxl'), self.dummy)

        out = gramex.data.download({'dummy': self.dummy, 'sales': self.sales}, format='xlsx')
        result = pd.read_excel(io.BytesIO(out), sheet_name=None, engine='openpyxl')
        afe(result['dummy'], self.dummy)
        afe(result['sales'], self.sales)

    def test_download_html(self):
        out = gramex.data.download(self.dummy, format='html')
        result = pd.read_html(io.BytesIO(out), encoding='utf-8')[0]
        afe(result, self.dummy, check_column_type=True)

        out = gramex.data.download(AttrDict([
            ('dummy', self.dummy),
            ('sales', self.sales)
        ]), format='html')
        result = pd.read_html(io.BytesIO(out), encoding='utf-8')
        afe(result[0], self.dummy, check_column_type=True)
        afe(result[1], self.sales, check_column_type=True)

    def test_template(self):
        raise SkipTest('TODO')


class FilterColsMixin(object):

    sales = gramex.cache.open(sales_file, 'xlsx')
    census = gramex.cache.open(sales_file, 'xlsx', sheet_name='census')

    def unique_of(self, data, cols):
        return data.groupby(cols).size().reset_index().drop(0, 1)

    def check_keys(self, result, keys):
        eq_(set(result.keys()), set(keys))

    def test_filtercols_frame(self):
        # ?_c=District returns up to 100 distinct values of the District column like
        # {'District': ['d1', 'd2', 'd3', ...]}
        cols = ['District']
        args = {'_c': cols}
        result = gramex.data.filtercols(args=args, **self.urls['census'])
        self.check_keys(result, cols)
        for key, val in result.items():
            eqframe(val, self.unique_of(self.census, key).head(100))

    def test_filtercols_limit(self):
        # ?_c=District&_limit=200 returns 200 values. (_limit= defaults to 100 values)
        cols = ['District']
        limit = 200
        args = {'_c': cols, '_limit': [limit]}
        result = gramex.data.filtercols(args=args, **self.urls['census'])
        self.check_keys(result, cols)
        for key, val in result.items():
            eqframe(val, self.unique_of(self.census, key).head(limit))

    def test_filtercols_multicols(self):
        # ?_c=city&_c=product returns distinct values for both City and Product like
        # {'City': ['c1', 'c1', ...], 'Product': ['p1', 'p2', ...]}
        cols = ['city', 'product']
        args = {'_c': cols}
        result = gramex.data.filtercols(args=args, **self.urls['sales'])
        self.check_keys(result, cols)
        for key, val in result.items():
            eqframe(val, self.unique_of(self.sales, key))

    def test_filtercols_sort_asc(self):
        # ?_c=City&_sort=City returns cities with data sorted by City sorted alphabetically
        cols = ['city']
        args = {'_c': cols, '_sort': ['city']}
        result = gramex.data.filtercols(args=args, **self.urls['sales'])
        self.check_keys(result, cols)
        for key, val in result.items():
            expected = self.unique_of(self.sales, key)
            eqframe(val, expected.sort_values('city'))

    def test_filtercols_sort_desc(self):
        # ?_c=City&_sort=-City returns cities with data sorted by City reverse alphabetically
        cols = ['city']
        args = {'_c': cols, '_sort': ['-city']}
        result = gramex.data.filtercols(args=args, **self.urls['sales'])
        self.check_keys(result, cols)
        for key, val in result.items():
            expected = self.unique_of(self.sales, key)
            eqframe(val, expected.sort_values('city', ascending=False))

    def test_filtercols_sort_desc_by_sales(self):
        raise SkipTest('TODO: FIX sort')
        # ?_c=City&_sort=-Sales returns cities with data sorted by largest sales first
        cols = ['city']
        args = {'_c': cols, '_sort': ['-sales']}
        result = gramex.data.filtercols(args=args, **self.urls['sales'])
        self.check_keys(result, cols)
        expected = self.sales.sort_values('sales', ascending=False)
        for key, val in result.items():
            eqframe(val, self.unique_of(expected, key))

    def test_filtercols_sort_by_city_and_sales(self):
        # ?_c=City&_sort=City&_sort=-Sales returns cities with data sorted by
        # city first, then by largest sales
        cols = ['city']
        args = {'_c': cols, '_sort': ['city', '-sales']}
        result = gramex.data.filtercols(args=args, **self.urls['sales'])
        self.check_keys(result, cols)
        expected = self.sales.sort_values(['city', 'sales'], ascending=[True, False])
        for key, val in result.items():
            eqframe(val, self.unique_of(expected, key))

    def test_filtercols_with_filter(self):
        # ?Product=p1&_c=City filters by Product=p1 and returns cities
        cols = ['District']
        args = {'_c': cols, 'State': ['KERALA']}
        result = gramex.data.filtercols(args=args, **self.urls['census'])
        self.check_keys(result, cols)
        expected = self.census[self.census['State'] == 'KERALA']
        for key, val in result.items():
            eqframe(val, self.unique_of(expected, key))

    def test_filtercols_multicols_with_filter(self):
        # ?Product=p1&_c=City&_c=Product filters by Product=p1 and returns
        # cities. But it returns products too -- UNFILTERED by Product=p1. (That
        # would only return p1!)
        cols = ['District', 'DistrictCaps']
        args = {'_c': cols, '_sort': ['State', 'District'], 'State': ['KERALA'],
                '_limit': [10]}
        result = gramex.data.filtercols(args=args, **self.urls['census'])
        self.check_keys(result, cols)
        filtered = self.census.sort_values(['State', 'District'])
        expected = filtered[filtered['State'] == 'KERALA']
        for key, val in result.items():
            eqframe(val, self.unique_of(expected, key).head(10))

    def test_filtercols_multicols_with_multifilter(self):
        raise SkipTest('TODO: FIX sort')
        # ?Product=p1&City=c1&_c=City&_c=Product returns Cities filtered by
        # Product=p1 (not City=c1), and Products filtered by City=c1 (not
        # Product=p1).
        cols = ['DistrictCaps']
        args = {'_c': cols, '_sort': ['State', 'District'],
                'State': ['KERALA'], 'District>~': ['K'], '_limit': [10]}
        result = gramex.data.filtercols(args=args, **self.urls['census'])
        self.check_keys(result, cols)
        df = self.census.sort_values(['State', 'District'])
        expected = df[df['State'].eq('KERALA') & df['District'].ge('K')]
        for key, val in result.items():
            eqframe(val, self.unique_of(expected, key).head(10))

    def test_filtercols_with_filter_unicode(self):
        # ?देश=भारत&_c=city filters by देश=भारत and returns cities
        cols = ['city']
        args = {'_c': cols, 'देश': ['भारत']}
        result = gramex.data.filtercols(args=args, **self.urls['sales'])
        self.check_keys(result, cols)
        expected = self.sales[self.sales['देश'] == 'भारत']
        for key, val in result.items():
            eqframe(val, self.unique_of(expected, key))

    def test_filtercols_with_filter_unicode_values(self):
        # ?देश=भारत&_c=product filters by देश=भारत and returns cities
        cols = ['product']
        args = {'_c': cols, 'देश': ['भारत']}
        result = gramex.data.filtercols(args=args, **self.urls['sales'])
        self.check_keys(result, cols)
        expected = self.sales[self.sales['देश'] == 'भारत']
        for key, val in result.items():
            eqframe(val, self.unique_of(expected, key))


class TestFilterColsFrame(unittest.TestCase, FilterColsMixin):
    urls = {
        'sales': {'url': FilterColsMixin.sales},
        'census': {'url': FilterColsMixin.census}
    }


class TestFilterColsDB(unittest.TestCase, FilterColsMixin):
    urls = {}

    @classmethod
    def setupClass(cls):
        cls.db = dbutils.sqlite_create_db(
            'test_filtercols.db',
            sales=cls.sales, census=cls.census)
        cls.urls = {
            'sales': {'url': cls.db, 'table': 'sales'},
            'census': {'url': cls.db, 'table': 'census'}
        }

    @classmethod
    def tearDownClass(cls):
        dbutils.sqlite_drop_db('test_filtercols.db')


class TestAlter(unittest.TestCase):
    sales = gramex.cache.open(sales_file, 'xlsx')
    db = set()

    def check_alter(self, url, id=999, age=4.5):
        # Add a new column of types str, int, float.
        # Also test default, nullable
        gramex.data.alter(url, table='sales', columns={
            'id': {'type': 'int'},
            'email': {'type': 'varchar(99)', 'nullable': True, 'default': 'none'},
            'age': {'type': 'float', 'nullable': False, 'default': age},
        })
        # New tables also support primary_key, autoincrement
        gramex.data.alter(url, table='new', columns={
            'id': {'type': 'int', 'primary_key': True, 'autoincrement': True},
            'email': {'type': 'varchar(99)', 'nullable': True, 'default': 'none'},
            'age': {'type': 'float', 'nullable': False, 'default': age},
        })
        engine = sa.create_engine(url)
        meta = sa.MetaData(bind=engine)
        meta.reflect()
        # Test types
        for table in (meta.tables['sales'], meta.tables['new']):
            eq_(table.columns.id.type.python_type, int)
            # eq_(table.columns.id.nullable, True)
            eq_(table.columns.email.type.python_type, str)
            # eq_(table.columns.email.nullable, True)
            eq_(table.columns.age.type.python_type, float)
            eq_(table.columns.age.nullable, False)
        # sales: insert and test row for default and types
        gramex.data.insert(url, table='sales', args={'id': [id]})
        result = gramex.data.filter(url, table='sales', args={'id': [id]})
        eq_(len(result), 1)
        eq_(result['id'].iloc[0], id)
        eq_(result['email'].iloc[0], 'none')
        eq_(result['age'].iloc[0], age)
        # new: test types
        gramex.data.insert(url, table='new', args={'age': [3.0, 4.0]})
        afe(gramex.data.filter(url, table='new'), pd.DataFrame([
            {'id': 1, 'email': 'none', 'age': 3.0},
            {'id': 2, 'email': 'none', 'age': 4.0},
        ]))

    def test_mysql(self):
        url = dbutils.mysql_create_db(server.mysql, 'test_alter', sales=self.sales)
        self.db.add('mysql')
        self.check_alter(url)

    def test_postgres(self):
        url = dbutils.postgres_create_db(server.postgres, 'test_alter', sales=self.sales)
        self.db.add('postgres')
        self.check_alter(url)

    def test_sqlite(self):
        url = dbutils.sqlite_create_db('test_alter.db', sales=self.sales)
        self.db.add('sqlite')
        self.check_alter(url)

    @classmethod
    def tearDownClass(cls):
        if 'mysql' in cls.db:
            dbutils.mysql_drop_db(server.mysql, 'test_alter')
        if 'postgres' in cls.db:
            dbutils.postgres_drop_db(server.postgres, 'test_alter')
        if 'sqlite' in cls.db:
            dbutils.sqlite_drop_db('test_alter.db')

# TODO: insert() and update() should auto-run alter()

# BUG: update() doesn't handle this right
# ?id=1&data=x&id=2&data=y
# {id: [1, 2], data: [x, y]}
