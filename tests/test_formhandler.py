# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import six
import shutil
import sqlite3
import pandas as pd
import gramex.cache
from io import BytesIO
from nose.tools import eq_, ok_
from gramex.http import BAD_REQUEST, FOUND
from gramex.config import variables, objectpath, merge
from pandas.util.testing import assert_frame_equal as afe
from . import folder, TestGramex, dbutils, tempfiles


class TestFormHandler(TestGramex):
    sales = gramex.cache.open(os.path.join(folder, 'sales.xlsx'), 'xlsx')

    def check_filter(self, url, df=None, na_position='last', key=None):
        # Modelled on testlib.test_data.TestFilter.check_filter

        def eq(args, expected):
            result = self.get(url, params=args).json()
            actual = pd.DataFrame(result[key] if key else result)
            expected.index = actual.index
            if len(expected) > 0:
                afe(actual, expected, check_like=True)

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
        afe(actual, expected, check_column_type=six.PY3)

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
            self.check_filter('/formhandler/sqlite-queryfunction', na_position='last')
            self.check_filter('/formhandler/sqlite-queryfunction?ct=Hyderabad&ct=Coimbatore',
                              na_position='last',
                              df=self.sales[self.sales['city'].isin(['Hyderabad', 'Coimbatore'])])
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

    def test_prepare(self):
        self.eq('/formhandler/prepare', self.sales[self.sales['product'] == 'Biscuit'])

    def test_download(self):
        # Modelled on testlib.test_data.TestDownload
        big = self.sales[self.sales['sales'] > 100]
        by_growth = self.sales.sort_values('growth')
        big.index = range(len(big))
        by_growth.index = range(len(by_growth))

        out = self.get('/formhandler/file?_format=html').content
        # Note: In Python 2, pd.read_html returns .columns.inferred_type=mixed
        # instead of unicde. So check column type only in PY3 not PY2
        afe(pd.read_html(out, encoding='utf-8')[0], self.sales, check_column_type=six.PY3)

        out = self.get('/formhandler/file-multi?_format=html').content
        result = pd.read_html(BytesIO(out), encoding='utf-8')
        afe(result[0], big, check_column_type=six.PY3)
        afe(result[1], by_growth, check_column_type=six.PY3)

        out = self.get('/formhandler/file?_format=xlsx').content
        afe(pd.read_excel(BytesIO(out)), self.sales)

        out = self.get('/formhandler/file-multi?_format=xlsx').content
        result = pd.read_excel(BytesIO(out), sheetname=None)
        afe(result['big'], big)
        afe(result['by-growth'], by_growth)

        out = self.get('/formhandler/file?_format=csv').content
        ok_(out.startswith(''.encode('utf-8-sig')))
        afe(pd.read_csv(BytesIO(out), encoding='utf-8'), self.sales)

        out = self.get('/formhandler/file-multi?_format=csv').content
        lines = out.splitlines(True)
        eq_(lines[0], 'big\n'.encode('utf-8-sig'))
        actual = pd.read_csv(BytesIO(b''.join(lines[1:len(big) + 2])), encoding='utf-8')
        afe(actual, big)
        eq_(lines[len(big) + 3], 'by-growth\n'.encode('utf-8'))
        actual = pd.read_csv(BytesIO(b''.join(lines[len(big) + 4:])), encoding='utf-8')
        afe(actual, by_growth)

    @staticmethod
    def copy_file(source, target):
        target = os.path.join(folder, target)
        source = os.path.join(folder, source)
        shutil.copyfile(source, target)
        tempfiles[target] = target
        return target

    def call(self, url, args, method, headers):
        r = self.check('/formhandler/edits-' + url, data=args, method=method, headers=headers)
        meta = r.json()
        # meta has 'ignored' with list of ignored columns
        ok_(['x', args.get('x', [1])] in objectpath(meta, 'data.ignored'))
        # meta has 'filters' for PUT and DELETE. It is empty for post
        if method.lower() == 'post':
            eq_(objectpath(meta, 'data.filters'), [])
        else:
            ok_(isinstance(objectpath(meta, 'data.filters'), list))
        return r

    def check_edit(self, method, source, args, count):
        # Edits the correct count of records, returns empty value and saves to file
        target = self.copy_file('sales.xlsx', 'sales-edits.xlsx')
        self.call('xlsx-' + source, args, method, {'Count-Data': str(count)})
        result = gramex.cache.open(target)
        # Check result. TODO: check that the values are correctly added
        if method == 'delete':
            eq_(len(result), len(self.sales) - count)
        elif method == 'post':
            eq_(len(result), len(self.sales) + count)
        elif method == 'put':
            eq_(len(result), len(self.sales))

        target = os.path.join(folder, 'formhandler-edits.db')
        dbutils.sqlite_create_db(target, sales=self.sales)
        tempfiles[target] = target
        self.call('sqlite-' + source, args, method, {'Count-Data': str(count)})
        # Check result. TODO: check that the values are correctly added
        con = sqlite3.connect(target)
        result = pd.read_sql('SELECT * FROM sales', con)
        # TODO: check that the values are correctly added
        if method == 'delete':
            eq_(len(result), len(self.sales) - count)
        elif method == 'post':
            eq_(len(result), len(self.sales) + count)
        elif method == 'put':
            eq_(len(result), len(self.sales))

    def test_edit_singlekey(self):
        # Operations with a single key works
        self.check_edit('post', 'singlekey', {
            'देश': ['भारत'],
            'city': ['Bangalore'],
            'product': ['Crème'],
            'sales': ['100'],
            'growth': ['0.32'],
        }, count=1)
        self.check_edit('put', 'singlekey', {
            'sales': ['513.7'],
            'city': [123],
            'product': ['abc'],
        }, count=1)
        # Delete with single ID as primary key works
        self.check_edit('delete', 'singlekey', {
            'sales': ['513.7']
        }, count=1)

    def test_edit_multikey_single_value(self):
        # POST single value
        self.check_edit('post', 'multikey', {
            'देश': ['भारत'],
            'city': ['Bangalore'],
            'product': ['Alpha'],
            'sales': ['100'],
        }, count=1)
        self.check_edit('put', 'multikey', {
            'देश': ['भारत'],
            'city': ['Bangalore'],
            'product': ['Eggs'],
            'sales': ['100'],
            'growth': ['0.32'],
        }, count=1)
        self.check_edit('delete', 'multikey', {
            'देश': ['भारत'],
            'city': ['Bangalore'],
            'product': ['Crème'],
        }, count=1)

    def test_edit_multikey_multi_value(self):
        self.check_edit('post', 'multikey', {
            'देश': ['भारत', 'भारत', 'भारत'],
            'city': ['Bangalore', 'Bangalore', 'Bangalore'],
            'product': ['Alpha', 'Beta', 'Gamma'],
            'sales': ['100', '', '300'],
            'growth': ['0.32', '0.50', '0.12'],
            # There is a default ?x=1. Override that temporarily
            'x': ['', '', '']
        }, count=3)
        # NOTE: PUT behaviour for multi-value is undefined
        self.check_edit('delete', 'multikey', {
            'देश': ['भारत', 'भारत', 'भारत', 'invalid'],
            'city': ['Bangalore', 'Bangalore', 'Bangalore', 'invalid'],
            'product': ['芯片', 'Eggs', 'Biscuit', 'invalid'],
        }, count=3)

    def test_edit_redirect(self):
        self.copy_file('sales.xlsx', 'sales-edits.xlsx')
        # redirect: affects POST, PUT and DELETE
        for method in ['post', 'put', 'delete']:
            r = self.get('/formhandler/edits-xlsx-redirect', method=method, data={
                'देश': ['भारत'],
                'city': ['Bangalore'],
                'product': ['Eggs'],
                'sales': ['100'],
            }, allow_redirects=False)
            eq_(r.status_code, FOUND)
            ok_('Count-Data' in r.headers)  # Any value is fine, we're not checking that
            eq_(r.headers['Location'], '/redirected')
        # GET is not redirected
        r = self.get('/formhandler/edits-xlsx-redirect', allow_redirects=False)
        ok_('Location' not in r.headers)

    def test_edit_multidata(self):
        csv_path = os.path.join(folder, 'sales-edits.csv')
        self.sales.to_csv(csv_path, index=False, encoding='utf-8')
        dbutils.mysql_create_db(variables.MYSQL_SERVER, 'test_formhandler', sales=self.sales)
        try:
            row = {'देश': 'भारत', 'city': 'X', 'product': 'Q', 'growth': None}
            self.check('/formhandler/edits-multidata', method='post', data={
                'csv:देश': ['भारत'],
                'csv:city': ['X'],
                'csv:product': ['Q'],
                'csv:sales': ['10'],
                'sql:देश': ['भारत'],
                'sql:city': ['X'],
                'sql:product': ['Q'],
                'sql:sales': ['20'],
            }, headers={
                'count-csv': '1',
                'count-sql': '1',
            })
            data = self.check('/formhandler/edits-multidata').json()
            eq_(data['csv'][-1], merge(row, {'sales': 10}))
            eq_(data['sql'][-1], merge(row, {'sales': 20}))
            eq_(len(data['csv']), len(self.sales) + 1)
            eq_(len(data['sql']), len(self.sales) + 1)

            self.check('/formhandler/edits-multidata', method='put', data={
                'csv:city': ['X'],
                'csv:product': ['Q'],
                'csv:sales': ['30'],
                'sql:city': ['X'],
                'sql:product': ['Q'],
                'sql:sales': ['40'],
            }, headers={
                'count-csv': '1',
                'count-sql': '1',
            })
            data = self.check('/formhandler/edits-multidata').json()
            eq_(data['csv'][-1], merge(row, {'sales': 30}))
            eq_(data['sql'][-1], merge(row, {'sales': 40}))
            eq_(len(data['csv']), len(self.sales) + 1)
            eq_(len(data['sql']), len(self.sales) + 1)

            self.check('/formhandler/edits-multidata', method='delete', data={
                'csv:city': ['X'],
                'csv:product': ['Q'],
                'sql:city': ['X'],
                'sql:product': ['Q'],
            }, headers={
                'count-csv': '1',
                'count-sql': '1',
            })
            data = self.check('/formhandler/edits-multidata').json()
            eq_(len(data['csv']), len(self.sales))
            eq_(len(data['sql']), len(self.sales))

        finally:
            dbutils.mysql_drop_db(variables.MYSQL_SERVER, 'test_formhandler')
            os.remove(csv_path)
