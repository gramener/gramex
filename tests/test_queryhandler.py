# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import requests
import pandas as pd
import sqlalchemy as sa
from pathlib import Path
import pandas.util.testing as pdt
from nose.plugins.skip import SkipTest
from . import server, TestGramex
import gramex.config
from gramex.http import OK


class QueryHandlerTestMixin(object):
    folder = Path(__file__).absolute().parent
    data = pd.read_csv(str(folder / 'actors.csv'))

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
        pdt.assert_frame_equal(self.data, pd.read_csv(base + '/csv/?limit=100'))

        pdt.assert_frame_equal(
            self.data.query('name == "Charlie Chaplin"').reset_index(drop=True),
            pd.read_json(base + '/json/?name=Charlie%20Chaplin').reset_index(drop=True)
        )

        pdt.assert_frame_equal(
            self.data.query('votes > 90').reset_index(drop=True),
            pd.read_html(base + '/html/?votes=90')[0].drop('Unnamed: 0', 1).reset_index(drop=True),
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

        eq(self.data[:5], pd.read_csv(base + 'csv/?limit=5'))

        eq(self.data[self.data.name.str.contains('Brando')],
           pd.read_json(base + 'json/like/?name=*Brando*'))

    def test_query_crud_db(self):
        insert_base = server.base_url + '/datastoreq/' + self.database + '/insert/'
        edit_base = server.base_url + '/datastoreq/' + self.database + '/edit/'
        delete_base = server.base_url + '/datastoreq/' + self.database + '/delete/'
        validation_base = server.base_url + '/datastoreq/' + self.database + '/validate/'

        def eq(base, method, payload, where, y):
            response = method(base, params=payload)
            self.assertEqual(response.status_code, OK)
            if y is None:
                self.assertEqual(len(requests.get(validation_base + where).text), 0)
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
    'Test QueryHandler for SQLite database via sqlalchemy driver'
    database = 'sqlite'

    @classmethod
    def setUpClass(cls):
        cls.db = cls.folder / 'actors.db'
        if cls.db.is_file():
            cls.db.unlink()
        cls.engine = sa.create_engine('sqlite:///' + str(cls.db))
        cls.data.to_sql('actors', con=cls.engine, index=False)

    @classmethod
    def tearDownClass(cls):
        if cls.db.is_file():
            cls.db.unlink()


class TestMysqlQueryHandler(TestGramex, QueryHandlerTestMixin):
    'Test QueryHandler for MySQL database via sqlalchemy driver'
    database = 'mysql'

    @classmethod
    def setUpClass(cls):
        cls.dburl = 'mysql+pymysql://root@%s/' % gramex.config.variables.MYSQL_SERVER
        cls.engine = sa.create_engine(cls.dburl)
        try:
            cls.engine.execute("DROP DATABASE IF EXISTS test_queryhandler")
            cls.engine.execute("CREATE DATABASE test_queryhandler "
                               "CHARACTER SET utf8 COLLATE utf8_general_ci")
            cls.engine.dispose()
            cls.engine = sa.create_engine(cls.dburl + 'test_queryhandler')
            cls.data.to_sql('actors', con=cls.engine, index=False)
        except sa.exc.OperationalError:
            raise SkipTest('Unable to connect to %s' % cls.dburl)

    @classmethod
    def tearDownClass(cls):
        cls.engine.execute("DROP DATABASE test_queryhandler")
        cls.engine.dispose()


class TestPostgresQueryHandler(TestGramex, QueryHandlerTestMixin):
    'Test QueryHandler for PostgreSQL database via sqlalchemy driver'
    database = 'postgresql'

    @classmethod
    def setUpClass(cls):
        cls.dburl = 'postgresql://postgres@%s/' % gramex.config.variables.POSTGRES_SERVER
        cls.engine = sa.create_engine(cls.dburl + 'postgres')
        try:
            conn = cls.engine.connect()
            conn.execute('commit')
            conn.execute('DROP DATABASE IF EXISTS test_queryhandler')
            conn.execute('commit')
            conn.execute("CREATE DATABASE test_queryhandler ENCODING 'UTF8'")
            conn.close()
            cls.engine = sa.create_engine(cls.dburl + 'test_queryhandler')
            cls.data.to_sql('actors', con=cls.engine, index=False)
            cls.engine.dispose()
        except sa.exc.OperationalError:
            raise SkipTest('Unable to connect to %s' % cls.dburl)

    @classmethod
    def tearDownClass(cls):
        cls.engine = sa.create_engine(cls.dburl + 'postgres')
        conn = cls.engine.connect()
        conn.execute('commit')
        # Terminate all other sessions using the test_queryhandler database
        conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                     "WHERE datname='test_queryhandler'")
        conn.execute('DROP DATABASE test_queryhandler')
        conn.close()
        cls.engine.dispose()
