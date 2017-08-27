# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import requests
import pandas as pd
from pathlib import Path
import pandas.util.testing as pdt
from . import server, TestGramex, dbutils
from gramex.config import variables
from gramex.http import OK


class QueryHandlerTestMixin(object):
    folder = Path(__file__).absolute().parent
    data = pd.read_csv(str(folder / 'actors.csv'), encoding='utf-8')

    def test_pingdb(self):
        url = '/datastoreq/' + self.database
        self.check(url + '/csv/?limit=5', code=200, headers={
            'Etag': True, 'X-Test': 'abc', 'Content-Disposition': 'attachment;filename=alpha.csv'})
        self.check(url + '/json/?name=Charlie%20Chaplin', code=200, headers={
            'Etag': True, 'X-Test': 'abc'})
        self.check(url + '/html/?votes=100', code=200, headers={
            'Etag': True, 'X-Test': 'abc'})
        self.check(url + '/xyz', code=404)

    def test_fetchdb(self):
        base = server.base_url + '/datastoreq/' + self.database
        pdt.assert_frame_equal(self.data, pd.read_csv(base + '/csv/?limit=100', encoding='utf-8'))

        pdt.assert_frame_equal(
            self.data.query('name == "Charlie Chaplin"').reset_index(drop=True),
            pd.read_json(base + '/json/?name=Charlie%20Chaplin').reset_index(drop=True)
        )

        pdt.assert_frame_equal(
            self.data.query('votes > 90').reset_index(drop=True),
            pd.read_html(base + '/html/?votes=90', encoding='utf-8')[0].reset_index(drop=True),
            check_less_precise=True
        )

    def test_querydb(self):
        def eq(a, b):
            return pdt.assert_frame_equal(a.reset_index(drop=True), b)

        def eqdt(a, b):
            return pdt.assert_frame_equal(a.reset_index(drop=True).sort_index(axis=1),
                                          b.sort_index(axis=1),
                                          check_dtype=False)

        base = server.base_url + '/datastoreq/' + self.database + '/'

        eq(self.data[:5], pd.read_csv(base + 'csv/?limit=5', encoding='utf-8'))

        eq(self.data[self.data.name.str.contains('Brando')],
           pd.read_json(base + 'json/like/?name=*Brando*'))

    def test_query_crud_db(self):
        insert_base = server.base_url + '/datastoreq/' + self.database + '/insert/'
        edit_base = server.base_url + '/datastoreq/' + self.database + '/edit/'
        delete_base = server.base_url + '/datastoreq/' + self.database + '/delete/'
        validation_base = server.base_url + '/datastoreq/' + self.database + '/validate/'

        def eq(url, method, params, where, y):
            # call url?params via method.
            response = method(url, params=params)
            self.assertEqual(response.status_code, OK)
            if y is None:
                self.assertEqual(len(requests.get(validation_base + where).text.strip()), 0)
            else:
                x = pd.read_csv(validation_base + where, encoding='utf-8')
                pdt.assert_frame_equal(x, pd.DataFrame(y))

        nan = pd.np.nan
        # create
        eq(insert_base, requests.post, {'name': 'xgram1', 'rating': 0.230, 'votes': 34},
           '?name=xgram1&votes=34&rating=0.230',
           [{'category': nan, 'name': 'xgram1', 'rating': 0.230, 'votes': 34}])

        eq(
            insert_base, requests.post,
            {'name': 'xgram3', 'votes': 20, 'rating': 0.450, 'category': 'a'},
            '?name=xgram3&votes=20&rating=0.450&category=a',
            [{'category': 'a', 'name': 'xgram3', 'rating': 0.450, 'votes': 20}]
        )

        # update
        eq(edit_base, requests.post, {'name': 'xgram1', 'votes': 11},
           '?name=xgram1',
           [{'category': nan, 'name': 'xgram1', 'rating': 0.230, 'votes': 11}])

        # delete
        eq(delete_base, requests.post, {'name': 'xgram1'}, '?name=xgram1', None)


class TestSqliteHandler(TestGramex, QueryHandlerTestMixin):
    # Test QueryHandler for SQLite database via sqlalchemy driver
    database = 'sqlite'

    @classmethod
    def setUpClass(cls):
        dbutils.sqlite_create_db('actors.db', actors=cls.data)

    @classmethod
    def tearDownClass(cls):
        dbutils.sqlite_drop_db('actors.db')

    def test_filename(self):
        self.check('/datastoreq/sqlite/csv/filename?limit=5', headers={
            'Content-Disposition': 'attachment;filename=top_actors.csv'})
        self.check('/datastoreq/sqlite/csv/filename?limit=5&filename=name.csv', headers={
            'Content-Disposition': 'attachment;filename=name.csv'})

    def test_multiquery(self):
        result = self.check('/datastoreq/sqlite/multiquery').json()
        self.assertEqual(result['name'], self.data[['name']][:5].to_dict(orient='records'))
        self.assertEqual(result['votes'], self.data[['votes']][:5].to_dict(orient='records'))

    def test_multiparams(self):
        result = self.check('/datastoreq/sqlite/multiparams').json()
        name_result = self.data[['name']][self.data['votes'] > 100].to_dict(orient='records')
        self.assertEqual(result['name'], name_result)
        self.assertEqual(result['votes'], self.data[['votes']][:5].to_dict(orient='records'))
        self.assertEqual(result['empty'], [])

    def test_template(self):
        result = self.check('/datastoreq/sqlite/csv/filename?limit=5&format=template').text
        self.assertIn('<!-- Comment for tests/test_queryhandler.py -->', result)

        result = self.check('/datastoreq/template').text
        self.assertIn('<!-- Test template -->', result)


class TestMysqlQueryHandler(TestGramex, QueryHandlerTestMixin):
    # Test QueryHandler for MySQL database via sqlalchemy driver
    database = 'mysql'

    @classmethod
    def setUpClass(cls):
        dbutils.mysql_create_db(variables.MYSQL_SERVER, 'test_queryhandler', actors=cls.data)

    @classmethod
    def tearDownClass(cls):
        dbutils.mysql_drop_db(variables.MYSQL_SERVER, 'test_queryhandler')


class TestPostgresQueryHandler(TestGramex, QueryHandlerTestMixin):
    # Test QueryHandler for PostgreSQL database via sqlalchemy driver
    database = 'postgresql'

    @classmethod
    def setUpClass(cls):
        dbutils.postgres_create_db(variables.POSTGRES_SERVER, 'test_queryhandler', actors=cls.data)

    @classmethod
    def tearDownClass(cls):
        dbutils.postgres_drop_db(variables.POSTGRES_SERVER, 'test_queryhandler')
