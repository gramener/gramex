# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import six
import dbutils
import pandas as pd
import gramex.cache
from io import BytesIO
from nose.tools import eq_, ok_
from gramex.http import BAD_REQUEST
from gramex.config import variables
from pandas.util.testing import assert_frame_equal
from . import folder, TestGramex


class TestFormHandler(TestGramex):
    sales = gramex.cache.open(os.path.join(folder, 'sales.xlsx'), 'xlsx')

    def check_filter(self, url, df=None, na_position='last', key=None):
        # Modelled on testlib.test_data.TestFilter.check_filter

        def eq(args, expected):
            result = self.get(url, params=args).json()
            actual = pd.DataFrame(result[key] if key else result)
            expected.index = actual.index
            if len(expected) > 0:
                assert_frame_equal(actual, expected, check_like=True)

        sales = self.sales if df is None else df

        eq({}, sales)
        eq({'देश': ['भारत']},
           sales[sales['देश'] == 'भारत'])
        eq({'city': ['Hyderabad', 'Coimbatore']},
           sales[sales['city'].isin(['Hyderabad', 'Coimbatore'])])
        eq({'product!': ['Biscuit', 'Crème']},
           sales[~sales['product'].isin(['Biscuit', 'Crème'])])
        eq({'city>': ['Bangalore'], 'city<': ['Singapore']},
           sales[(sales['city'] > 'Bangalore') & (sales['city'] < 'Singapore')])
        eq({'city>~': ['Bangalore'], 'city<~': ['Singapore']},
           sales[(sales['city'] >= 'Bangalore') & (sales['city'] <= 'Singapore')])
        eq({'city~': ['ore']},
           sales[sales['city'].str.contains('ore')])
        eq({'product': ['Biscuit'], 'city': ['Bangalore'], 'देश': ['भारत']},
           sales[(sales['product'] == 'Biscuit') & (sales['city'] == 'Bangalore') &
                 (sales['देश'] == 'भारत')])
        eq({'city!~': ['ore']},
           sales[~sales['city'].str.contains('ore')])
        eq({'sales>': ['100'], 'sales<': ['1000']},
           sales[(sales['sales'] > 100) & (sales['sales'] < 1000)])
        eq({'growth<': [0.5]},
           sales[sales['growth'] < 0.5])
        eq({'sales>': ['100'], 'sales<': ['1000'], 'growth<': ['0.5']},
           sales[(sales['sales'] > 100) & (sales['sales'] < 1000) & (sales['growth'] < 0.5)])
        eq({'देश': ['भारत'], '_sort': ['sales']},
           sales[sales['देश'] == 'भारत'].sort_values('sales', na_position=na_position))
        eq({'product<~': ['Biscuit'], '_sort': ['-देश', '-growth']},
           sales[sales['product'] == 'Biscuit'].sort_values(
                ['देश', 'growth'], ascending=[False, False], na_position=na_position))
        eq({'देश': ['भारत'], '_offset': ['4'], '_limit': ['8']},
           sales[sales['देश'] == 'भारत'].iloc[4:12])

        cols = ['product', 'city', 'sales']
        eq({'देश': ['भारत'], '_c': cols},
           sales[sales['देश'] == 'भारत'][cols])

        ignore_cols = ['product', 'city']
        eq({'देश': ['भारत'], '_c': ['-' + c for c in ignore_cols]},
           sales[sales['देश'] == 'भारत'][[c for c in sales.columns if c not in ignore_cols]])

        # Non-existent column does not raise an error for any operation
        for op in ['', '~', '!', '>', '<', '<~', '>', '>~']:
            eq({'nonexistent' + op: ['']}, sales)
        # Non-existent sorts do not raise an error
        eq({'_sort': ['nonexistent', 'sales']},
           sales.sort_values('sales', na_position=na_position))
        # Non-existent _c does not raise an error
        eq({'_c': ['nonexistent', 'sales']}, sales[['sales']])

        # Invalid limit or offset raise an error
        eq_(self.get(url, params={'_limit': ['abc']}).status_code, BAD_REQUEST)
        eq_(self.get(url, params={'_offset': ['abc']}).status_code, BAD_REQUEST)

    def eq(self, url, expected):
        out = self.get(url).content
        actual = pd.read_csv(BytesIO(out), encoding='utf-8')
        expected.index = range(len(expected))
        assert_frame_equal(actual, expected, check_column_type=six.PY3)

    def test_file(self):
        self.check_filter('/formhandler/file', na_position='last')
        self.check_filter('/formhandler/file-multi', na_position='last', key='big',
                          df=self.sales[self.sales['sales'] > 100])
        self.check_filter('/formhandler/file-multi', na_position='last', key='by-growth',
                          df=self.sales.sort_values('growth'))

    def test_sqlite(self):
        dbutils.sqlite_create_db('formhandler.db', sales=self.sales)
        try:
            self.check_filter('/formhandler/sqlite', na_position='first')
            self.check_filter('/formhandler/sqlite-multi', na_position='last', key='big',
                              df=self.sales[self.sales['sales'] > 100])
            self.check_filter('/formhandler/sqlite-multi', na_position='last', key='by-growth',
                              df=self.sales.sort_values('growth'))
            self.check_filter('/formhandler/sqlite-multi', na_position='last', key='big-by-growth',
                              df=self.sales[self.sales['sales'] > 100].sort_values('growth'))
        finally:
            try:
                dbutils.sqlite_drop_db('formhandler.db')
            except OSError:
                pass

    def test_mysql(self):
        dbutils.mysql_create_db(variables.MYSQL_SERVER, 'test_formhandler', sales=self.sales)
        try:
            self.check_filter('/formhandler/mysql', na_position='first')
        finally:
            dbutils.mysql_drop_db(variables.MYSQL_SERVER, 'test_formhandler')

    def test_postgres(self):
        dbutils.postgres_create_db(variables.POSTGRES_SERVER, 'test_formhandler', sales=self.sales)
        try:
            self.check_filter('/formhandler/postgres', na_position='last')
        finally:
            dbutils.postgres_drop_db(variables.POSTGRES_SERVER, 'test_formhandler')

    def test_default(self):
        cutoff, limit = 50, 2
        self.eq('/formhandler/default', self.sales[self.sales['sales'] > cutoff].head(limit))

    def test_modify(self):
        self.eq('/formhandler/modify', self.sales.sum(numeric_only=True).to_frame().T)

    def test_download(self):
        # Modelled on testlib.test_data.TestDownload
        big = self.sales[self.sales['sales'] > 100]
        by_growth = self.sales.sort_values('growth')
        big.index = range(len(big))
        by_growth.index = range(len(by_growth))

        out = self.get('/formhandler/file?_format=html').content
        # Note: In Python 2, pd.read_html returns .columns.inferred_type=mixed
        # instead of unicde. So check column type only in PY3 not PY2
        assert_frame_equal(pd.read_html(out, encoding='utf-8')[0], self.sales,
                           check_column_type=six.PY3)

        out = self.get('/formhandler/file-multi?_format=html').content
        result = pd.read_html(BytesIO(out), encoding='utf-8')
        assert_frame_equal(result[0], big, check_column_type=six.PY3)
        assert_frame_equal(result[1], by_growth, check_column_type=six.PY3)

        out = self.get('/formhandler/file?_format=xlsx').content
        assert_frame_equal(pd.read_excel(BytesIO(out)), self.sales)

        out = self.get('/formhandler/file-multi?_format=xlsx').content
        result = pd.read_excel(BytesIO(out), sheetname=None)
        assert_frame_equal(result['big'], big)
        assert_frame_equal(result['by-growth'], by_growth)

        out = self.get('/formhandler/file?_format=csv').content
        ok_(out.startswith(''.encode('utf-8-sig')))
        assert_frame_equal(pd.read_csv(BytesIO(out), encoding='utf-8'), self.sales)

        out = self.get('/formhandler/file-multi?_format=csv').content
        lines = out.splitlines(True)
        eq_(lines[0], 'big\n'.encode('utf-8-sig'))
        actual = pd.read_csv(BytesIO(b''.join(lines[1:len(big) + 2])), encoding='utf-8')
        assert_frame_equal(actual, big)
        eq_(lines[len(big) + 3], 'by-growth\n'.encode('utf-8'))
        actual = pd.read_csv(BytesIO(b''.join(lines[len(big) + 4:])), encoding='utf-8')
        assert_frame_equal(actual, by_growth)
