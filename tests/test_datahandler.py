# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import requests
import pandas as pd
from pathlib import Path
from nose.tools import nottest
import pandas.util.testing as pdt
from . import server, TestGramex, dbutils
from gramex.config import variables
from gramex.http import OK, NOT_FOUND, INTERNAL_SERVER_ERROR


class DataHandlerTestMixin(object):
    folder = Path(__file__).absolute().parent
    data = pd.read_csv(str(folder / 'actors.csv'), encoding='utf-8')

    def test_pingdb(self):
        for frmt in ['json', 'html']:
            self.check('/datastore/%s/%s/?count=1' % (self.database, frmt), code=200, headers={
                'Etag': True, 'X-Test': 'abc'})
        for frmt in ['csv', 'xlsx']:
            self.check('/datastore/%s/%s/?count=1' % (self.database, frmt), code=200, headers={
                'Etag': True, 'X-Test': 'abc',
                'Content-Disposition': 'attachment;filename=alpha.%s' % frmt})
        self.check('/datastore/' + self.database + '/xyz', code=404)

    def test_fetchdb(self):
        base = server.base_url + '/datastore/' + self.database
        pdt.assert_frame_equal(self.data, pd.read_csv(base + '/csv/', encoding='utf-8'))
        pdt.assert_frame_equal(self.data, pd.read_json(base + '/json/'))
        pdt.assert_frame_equal(self.data, pd.read_html(base + '/html/', encoding='utf-8')[0],
                               check_less_precise=True)
        pdt.assert_frame_equal(self.data, pd.read_excel(base + '/xlsx/'))

    def test_querydb(self):
        def eq(a, b):
            return pdt.assert_frame_equal(a.reset_index(drop=True), b)

        def eqdt(a, b, sort_col='category'):
            return pdt.assert_frame_equal(
                a.sort_values(sort_col).reset_index(drop=True),
                b.sort_values(sort_col).reset_index(drop=True),
                check_dtype=False,  # dtype can be different
            )

        # select, where, sort, offset, limit
        base = server.base_url + '/datastore/' + self.database + '/'

        def get(q):
            return pd.read_csv(base + 'csv/' + q, encoding='utf-8')

        eq(self.data[:5], get('?limit=5'))
        eq(self.data[5:], get('?offset=5'))
        eq(self.data, get('?sort='))
        eq(self.data, get('?sort=nonexistent'))
        eq(self.data.sort_values(by='votes'), get('?sort=votes'))
        eq(self.data.sort_values(by='votes', ascending=False)[:5], get('?limit=5&sort=votes:desc'))
        eq(self.data.sort_values(by=['category', 'name'], ascending=[False, False]),
           get('?sort=category:desc&sort=name:desc'))
        eq(self.data[['name', 'votes']], get('?select=name&select=votes'))
        eq(self.data.query('category=="Actors"'), get('?where=category==Actors'))
        eq(self.data.query('category=="Actors"'), get('?where=category=Actors'))
        eq(self.data.query('category!="Actors"'), get('?where=category!=Actors'))
        eq(self.data.query('category=="Actors"'), get('?where=category=Actors&where=name='))
        eq(self.data.query('category=="Actors"'), get('?where=category=Actors&where=na='))
        eq(self.data.query('category=="Actors"'), get('?where=category=Actors&where=votes>'))
        eq(self.data[self.data.name.str.contains('Brando')], get('?where=name~Brando'))
        eq(self.data[~self.data.name.str.contains('Brando')], get('?where=name!~Brando'))
        eq(self.data.query('votes>100'), get('?where=votes>100'))
        eq(self.data.query('150 > votes > 100'), get('?where=votes<150&where=votes>100&xyz=8765'))
        # ?q=a%e matches "Actresses" (category) and Charlie, James & Astaire (name)
        q = re.compile(r'a.*e', re.IGNORECASE).search
        result = self.data.T.apply(lambda row: bool(q(row['name']) or q(row['category'])))
        eq(self.data[result], get('?q=a%e'))

        # format
        eq(self.data[:5], get('?limit=5'))
        eq(self.data[:5], pd.read_json(base + 'csv/?limit=5&format='))
        eq(self.data[:5], pd.read_json(base + 'csv/?limit=5&format=json'))
        eq(self.data[:5], pd.read_json(base + 'csv/?limit=5&format=xx&format=json'))
        r = requests.get(base + 'csv/?limit=5&format=nonexistent')
        self.assertEqual(r.status_code, INTERNAL_SERVER_ERROR)

        # Aggregation cases
        eqdt((self.data.groupby('category', as_index=False)
              .agg({'rating': 'min', 'votes': 'sum'})
              .rename(columns={'rating': 'ratemin', 'votes': 'votesum'})),
             get('?groupby=category' +
                 '&agg=ratemin:min(rating)&agg=votesum:sum(votes)'))

        eqdt((self.data.query('120 > votes > 60')
              .groupby('category', as_index=False)
              .agg({'rating': 'max', 'votes': 'count'})
              .rename(columns={'rating': 'ratemax', 'votes': 'votecount'})
              .sort_values(by='votecount', ascending=True)),
             get('?groupby=category' +
                 '&agg=ratemax:max(rating)&agg=votecount:count(votes)' +
                 '&where=votes<120&where=votes>60&sort=votecount:asc'))

        eqdt((self.data.query('120 > votes > 60')
              .groupby('category', as_index=False)
              .agg({'rating': pd.np.mean, 'votes': pd.Series.nunique})
              .rename(columns={'rating': 'ratemean', 'votes': 'votenu'})
              .loc[1:, ['category', 'votenu']]),
             get('?groupby=category' +
                 '&agg=ratemean:mean(rating)&agg=votenu:nunique(votes)' +
                 '&where=votes<120&where=votes>60' +
                 '&select=category&select=votenu&offset=1'))

    def test_querypostdb(self):
        base = server.base_url + '/datastore/' + self.database + '/csv/'

        def eq(method, payload, data, where, b):
            response = method(base, params=payload, data=data)
            self.assertEqual(response.status_code, OK)
            a = pd.read_csv(base + where, encoding='utf-8')
            if b is None:
                self.assertEqual(len(a), 0)
            else:
                pdt.assert_frame_equal(a, pd.DataFrame(b))

        nan = pd.np.nan
        # create
        eq(requests.post, '', {'val': 'name=xgram1'},
           '?where=name=xgram1',
           [{'category': nan, 'name': 'xgram1', 'rating': nan, 'votes': nan}])
        eq(requests.post, 'val=name=xgram2', {},
           '?where=name=xgram2',
           [{'category': nan, 'name': 'xgram2', 'rating': nan, 'votes': nan}])
        eq(requests.post, 'val=name=xgram3&val=votes=20', {},
           '?where=name=xgram3&where=votes=20',
           [{'category': nan, 'name': 'xgram3', 'rating': nan, 'votes': 20}])
        eq(requests.post, 'val=name=xgram=x', {},
           '?where=name=xgram=x',
           [{'category': nan, 'name': 'xgram=x', 'rating': nan, 'votes': nan}])
        # update
        eq(requests.put, 'where=name=xgram1', {'val': 'votes=11'},
           '?where=name=xgram1',
           [{'category': nan, 'name': 'xgram1', 'rating': nan, 'votes': 11}])
        # read
        self.assertEqual(pd.read_csv(base + '?where=name~xgram', encoding='utf-8').shape[0], 4)
        # delete
        eq(requests.delete, 'where=name~xgram', {}, '?where=name~xgram', None)

        # crud with special chars
        ascii_min, ascii_max = 32, 128
        val = 'xgram-' + ''.join(chr(x) for x in range(ascii_min, ascii_max)) + 'ασλÆ©á '
        safe_val = requests.utils.quote(val.encode('utf8'))
        eq(requests.post, {'val': 'name=' + val}, {},
           '?where=name=' + safe_val,
           [{'category': nan, 'name': val, 'rating': nan, 'votes': nan}])
        eq(requests.put, {'where': 'name=' + val}, {'val': 'votes=1'},
           '?where=name=' + safe_val,
           [{'category': nan, 'name': val, 'rating': nan, 'votes': 1}])
        eq(requests.delete, {'where': 'name=' + val}, {},
           '?where=name=' + safe_val, None)

        # Edge cases
        # POST val is empty -- Insert an empty dict
        requests.post(base, data={})
        self.assertEqual(pd.read_csv(base, encoding='utf-8').isnull().all(axis=1).sum(), 1)
        cases = [
            # PUT val is empty -- raise error that VALS is required
            {'method': requests.put, 'data': {'where': 'name=xgram'}},
            # PUT  where is empty -- raise error that WHERE is required
            {'method': requests.put, 'data': {'val': 'name=xgram'}},
            # DELETE where is empty -- raise error that WHERE is required
            {'method': requests.delete, 'data': {}},
        ]
        for case in cases:
            response = case['method'](base, data=case['data'])
            self.assertEqual(response.status_code, NOT_FOUND)


class SqliteHandler(TestGramex, DataHandlerTestMixin):
    database = 'sqlite'

    @classmethod
    def setUpClass(cls):
        dbutils.sqlite_create_db('actors.db', actors=cls.data)

    @classmethod
    def tearDownClass(cls):
        dbutils.sqlite_drop_db('actors.db')


class TestSqliteHandler(SqliteHandler):
    # Test DataHandler for SQLite database via sqlalchemy driver

    def test_filename(self):
        self.check('/datastore/sqlite/csv/filename?limit=5', headers={
            'Content-Disposition': 'attachment;filename=top_actors.csv'})
        self.check('/datastore/sqlite/csv/filename?limit=5&filename=name.csv', headers={
            'Content-Disposition': 'attachment;filename=name.csv'})

    def test_template(self):
        result = self.check('/datastore/sqlite/csv/filename?limit=5&format=template').text
        self.assertIn('<!-- Comment for tests/test_datahandler.py -->', result)

        result = self.check('/datastore/template').text
        self.assertIn('<!-- Test template -->', result)


class TestMysqlDataHandler(TestGramex, DataHandlerTestMixin):
    # Test DataHandler for MySQL database via sqlalchemy driver
    database = 'mysql'

    @classmethod
    def setUpClass(cls):
        dbutils.mysql_create_db(variables.MYSQL_SERVER, 'test_datahandler', actors=cls.data)

    @classmethod
    def tearDownClass(cls):
        dbutils.mysql_drop_db(variables.MYSQL_SERVER, 'test_datahandler')


class TestPostgresDataHandler(TestGramex, DataHandlerTestMixin):
    # Test DataHandler for PostgreSQL database via sqlalchemy driver
    database = 'postgresql'

    @classmethod
    def setUpClass(cls):
        dbutils.postgres_create_db(variables.POSTGRES_SERVER, 'test_datahandler', actors=cls.data)

    @classmethod
    def tearDownClass(cls):
        dbutils.postgres_drop_db(variables.POSTGRES_SERVER, 'test_datahandler')


# odo tests fails on Anaconda 5.0. DataHandler is deprecated anyway
# https://code.gramener.com/cto/gramex/-/jobs/53708
@nottest
class TestBlazeDataHandler(SqliteHandler):
    # Test DataHandler for SQLite database via blaze driver
    database = 'blazesqlite'

    def test_querypostdb(self):
        # POST is not implemented for Blaze driver
        pass


@nottest
class TestBlazeMysqlDataHandler(TestMysqlDataHandler, TestBlazeDataHandler):
    database = 'blazemysql'

    def test_querypostdb(self):
        # POST is not implemented for Blaze driver
        pass


@nottest
class TestDataHandlerConfig(SqliteHandler):
    database = 'sqliteconfig'

    def test_pingdb(self):
        # We've already run this test in TestSqliteHandler
        pass

    def test_fetchdb(self):
        # We've already run this test in TestSqliteHandler
        pass

    def test_querypostdb(self):
        # We've already run this test in TestSqliteHandler
        pass

    def test_querydb(self):
        def eq(a, b):
            return pdt.assert_frame_equal(a.reset_index(drop=True), b)

        def dbcase(case):
            return '%s/datastore/%s%d/' % (server.base_url, self.database, case)

        eq(self.data.query('votes < 120')[:5],
           pd.read_csv(dbcase(1) + 'csv/?limit=5', encoding='utf-8'))
        eq(self.data.query('votes > 120')[:5],
           pd.read_csv(dbcase(1) + 'csv/?where=votes>120&limit=5', encoding='utf-8'))
        eq(self.data.query('votes < 120')[:5],
           pd.read_csv(dbcase(2) + 'csv/?limit=5', encoding='utf-8'))
        eq(self.data.query('votes < 120')[:5],
           pd.read_csv(dbcase(3) + 'csv/?limit=5', encoding='utf-8'))
        eq(self.data.query('votes < 120')[:5],
           pd.read_csv(dbcase(3) + 'csv/?where=votes>120&limit=5', encoding='utf-8'))
        eq(self.data.query('votes < 120').loc[:, ['rating', 'votes']],
           pd.read_csv(dbcase(4) + 'csv/?where=votes>120' +
                       '&select=rating&select=votes', encoding='utf-8'))
        eq(self.data.query('votes < 120').loc[:, ['rating', 'votes']],
           pd.read_csv(dbcase(5) + 'csv/?where=votes>120' +
                       '&select=rating&select=votes', encoding='utf-8'))
        eq((self.data.query('votes < 120 and rating > 0.4')
            .groupby('category', as_index=False)
            .agg({'rating': pd.np.mean, 'votes': pd.Series.nunique})
            .rename(columns={'rating': 'ratemean', 'votes': 'votenu'})
            .loc[:, ['category', 'votenu']]),
           pd.read_csv(dbcase(6) + 'csv/', encoding='utf-8'))
        # 7: no matter what the URL args are, votes, limit & format are frozen
        eq(self.data.query('votes < 120')[:5],
           pd.read_csv(dbcase(7) + 'csv/?votes=99&limit=99&format=json', encoding='utf-8'))
