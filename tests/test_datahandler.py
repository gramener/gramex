import pandas as pd
import sqlalchemy as sa
import pandas.util.testing as pdt
from pathlib import Path
from nose.plugins.skip import SkipTest
from .test_handlers import TestGramex
from . import server
import gramex.config

setUpModule = server.start_gramex
tearDownModule = server.stop_gramex


class DataHandlerTestMixin(object):
    folder = Path(__file__).absolute().parent
    data = pd.read_csv(str(folder / 'actors.csv'))

    def test_pingdb(self):
        for frmt in ['csv', 'json', 'html']:
            self.check('/datastore/%s/%s/' % (self.database, frmt), code=200)
        self.check('/datastore/' + self.database + '/xyz', code=404)

    def test_fetchdb(self):
        base = server.base_url + '/datastore/' + self.database
        pdt.assert_frame_equal(self.data, pd.read_csv(base + '/csv/'))
        pdt.assert_frame_equal(self.data, pd.read_json(base + '/json/'))
        pdt.assert_frame_equal(self.data, pd.read_html(base + '/html/')[0]
                               .drop('Unnamed: 0', 1), check_less_precise=True)

    def test_querydb(self):
        def eq(a, b):
            return pdt.assert_frame_equal(a.reset_index(drop=True), b)

        def eqdt(a, b):
            return pdt.assert_frame_equal(a.reset_index(drop=True).sort_index(axis=1),
                                          b.sort_index(axis=1),
                                          check_dtype=False)

        # select, where, sort, offset, limit
        base = server.base_url + '/datastore/' + self.database + '/'
        eq(self.data[:5],
           pd.read_csv(base + 'csv/?limit=5'))
        eq(self.data[5:],
           pd.read_csv(base + 'csv/?offset=5'))
        eq(self.data.sort_values(by='votes'),
           pd.read_csv(base + 'csv/?sort=votes'))
        eq(self.data.sort_values(by='votes', ascending=False)[:5],
           pd.read_csv(base + 'csv/?limit=5&sort=votes:desc'))
        eq(self.data.sort_values(by=['category', 'name'], ascending=[False, False]),
           pd.read_csv(base + 'csv/?sort=category:desc&sort=name:desc'))
        eq(self.data[['name', 'votes']],
           pd.read_csv(base + 'csv/?select=name&select=votes'))
        eq(self.data.query('category=="Actors"'),
           pd.read_csv(base + 'csv/?where=category==Actors'))
        eq(self.data.query('category=="Actors"'),
           pd.read_csv(base + 'csv/?where=category=Actors'))
        eq(self.data.query('category!="Actors"'),
           pd.read_csv(base + 'csv/?where=category!=Actors'))
        eq(self.data[self.data.name.str.contains('Brando')],
           pd.read_csv(base + 'csv/?where=name~Brando'))
        eq(self.data[~self.data.name.str.contains('Brando')],
           pd.read_csv(base + 'csv/?where=name!~Brando'))
        eq(self.data.query('votes>100'),
           pd.read_csv(base + 'csv/?where=votes>100'))
        eq(self.data.query('150 > votes > 100'),
           pd.read_csv(base + 'csv/?where=votes<150&where=votes>100&xyz=8765'))

        # Aggregation cases
        eqdt((self.data.groupby('category', as_index=False)
              .agg({'rating': 'min', 'votes': 'sum'})
              .rename(columns={'rating': 'ratemin', 'votes': 'votesum'})),
             pd.read_csv(base + 'csv/?groupby=category' +
                         '&agg=ratemin:min(rating)&agg=votesum:sum(votes)'))

        eqdt((self.data.query('120 > votes > 60')
              .groupby('category', as_index=False)
              .agg({'rating': 'max', 'votes': 'count'})
              .rename(columns={'rating': 'ratemax', 'votes': 'votecount'})
              .sort_values(by='votecount', ascending=True)),
             pd.read_csv(base + 'csv/?groupby=category' +
                         '&agg=ratemax:max(rating)&agg=votecount:count(votes)' +
                         '&where=votes<120&where=votes>60&sort=votecount:asc'))

        eqdt((self.data.query('120 > votes > 60')
              .groupby('category', as_index=False)
              .agg({'rating': pd.np.mean, 'votes': pd.Series.nunique})
              .rename(columns={'rating': 'ratemean', 'votes': 'votenu'})
              .loc[1:, ['category', 'votenu']]),
             pd.read_csv(base + 'csv/?groupby=category' +
                         '&agg=ratemean:mean(rating)&agg=votenu:nunique(votes)' +
                         '&where=votes<120&where=votes>60' +
                         '&select=category&select=votenu&offset=1'))


class TestSqliteHandler(TestGramex, DataHandlerTestMixin):
    'Test DataHandler for SQLite database via sqlalchemy driver'
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


class TestMysqlDataHandler(TestGramex, DataHandlerTestMixin):
    'Test DataHandler for MySQL database via sqlalchemy driver'
    database = 'mysql'

    @classmethod
    def setUpClass(cls):
        cls.dburl = 'mysql+pymysql://root@%s/' % gramex.config.variables.MYSQL_SERVER
        cls.engine = sa.create_engine(cls.dburl)
        try:
            cls.engine.execute("DROP DATABASE IF EXISTS test_datahandler")
            cls.engine.execute("CREATE DATABASE test_datahandler")
            cls.engine.dispose()
            cls.engine = sa.create_engine(cls.dburl + 'test_datahandler')
            cls.data.to_sql('actors', con=cls.engine, index=False)
        except sa.exc.OperationalError:
            raise SkipTest('Unable to connect to %s' % cls.dburl)

    @classmethod
    def tearDownClass(cls):
        cls.engine.execute("DROP DATABASE test_datahandler")
        cls.engine.dispose()


class TestPostgresDataHandler(TestGramex, DataHandlerTestMixin):
    'Test DataHandler for PostgreSQL database via sqlalchemy driver'
    database = 'postgresql'

    @classmethod
    def setUpClass(cls):
        cls.dburl = 'postgresql://postgres@%s/' % gramex.config.variables.POSTGRES_SERVER
        cls.engine = sa.create_engine(cls.dburl + 'postgres')
        try:
            conn = cls.engine.connect()
            conn.execute('commit')
            conn.execute('DROP DATABASE IF EXISTS test_datahandler')
            conn.execute('commit')
            conn.execute('CREATE DATABASE test_datahandler')
            conn.close()
            cls.engine = sa.create_engine(cls.dburl + 'test_datahandler')
            cls.data.to_sql('actors', con=cls.engine, index=False)
            cls.engine.dispose()
        except sa.exc.OperationalError:
            raise SkipTest('Unable to connect to %s' % cls.dburl)

    @classmethod
    def tearDownClass(cls):
        cls.engine = sa.create_engine(cls.dburl + 'postgres')
        conn = cls.engine.connect()
        conn.execute('commit')
        # Terminate all other sessions using the test_datahandler database
        conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                     "WHERE datname='test_datahandler'")
        conn.execute('DROP DATABASE test_datahandler')
        conn.close()
        cls.engine.dispose()


class TestBlazeDataHandler(TestSqliteHandler):
    'Test DataHandler for SQLite database via blaze driver'
    database = 'blazesqlite'


class TestBlazeMysqlDataHandler(TestMysqlDataHandler, TestBlazeDataHandler):
    'Test DataHandler for MySQL database via blaze driver'
    database = 'blazemysql'


class TestDataHandlerConfig(TestSqliteHandler):
    'Test DataHandler'
    database = 'sqliteconfig'

    def test_pingdb(self):
        pass

    def test_fetchdb(self):
        pass

    def test_querydb(self):
        def eq(a, b):
            return pdt.assert_frame_equal(a.reset_index(drop=True), b)

        def dbcase(case):
            return '%s/datastore/%s%d/' % (server.base_url, self.database, case)

        eq(self.data.query('votes < 120')[:5],
           pd.read_csv(dbcase(1) + 'csv/?limit=5'))
        eq(self.data.query('votes > 120')[:5],
           pd.read_csv(dbcase(1) + 'csv/?where=votes>120&limit=5'))
        eq(self.data.query('votes < 120')[:5],
           pd.read_csv(dbcase(2) + 'csv/?limit=5'))
        eq(self.data.query('votes < 120')[:5],
           pd.read_csv(dbcase(3) + 'csv/?limit=5'))
        eq(self.data.query('votes < 120')[:5],
           pd.read_csv(dbcase(3) + 'csv/?where=votes>120&limit=5'))
        eq(self.data.query('votes < 120').loc[:, ['rating', 'votes']],
           pd.read_csv(dbcase(4) + 'csv/?where=votes>120' +
                       '&select=rating&select=votes'))
        eq(self.data.query('votes < 120').loc[:, ['rating', 'votes']],
           pd.read_csv(dbcase(5) + 'csv/?where=votes>120' +
                       '&select=rating&select=votes'))
        eq((self.data.query('votes < 120 and rating > 0.4')
            .groupby('category', as_index=False)
            .agg({'rating': pd.np.mean, 'votes': pd.Series.nunique})
            .rename(columns={'rating': 'ratemean', 'votes': 'votenu'})
            .loc[:, ['category', 'votenu']]),
           pd.read_csv(dbcase(6) + 'csv/'))
        # 7: no matter what the URL args are, votes, limit & format are frozen
        eq(self.data.query('votes < 120')[:5],
           pd.read_csv(dbcase(7) + 'csv/?votes=99&limit=99&format=json'))
