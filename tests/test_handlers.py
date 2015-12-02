import os
import sys
import json
import requests
import markdown
import unittest
import subprocess
import pandas as pd
import sqlalchemy as sa
from pathlib import Path
import pandas.util.testing as pdt
from orderedattrdict import AttrDict
from nose.plugins.skip import SkipTest
from gramex.transforms import badgerfish

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

info = AttrDict(
    folder=Path(__file__).absolute().parent,
    process=None,
)


def setUpModule():
    'Run Gramex in this folder using the current gramex.conf.yaml'
    # Ensure that PYTHONPATH has this repo and ONLY this repo
    env = dict(os.environ)
    env['PYTHONPATH'] = str(info.folder.parent)
    info.process = subprocess.Popen(
        [sys.executable, '-m', 'gramex'],
        cwd=str(info.folder),
        env=env,
        stdout=getattr(subprocess, 'DEVNULL', open(os.devnull, 'w')),
    )


def tearDownModule():
    'Terminate Gramex'
    info.process.terminate()


class TestGramex(unittest.TestCase):
    'Base class to test Gramex running as a subprocess'
    base = 'http://localhost:9999'

    def get(self, url, **kwargs):
        return requests.get(self.base + url, **kwargs)

    def check(self, url, path=None, code=200, text=None):
        r = self.get(url)
        self.assertEqual(r.status_code, code, url)
        if text is not None:
            self.assertIn(text, r.text, '%s: %s != %s' % (url, text, r.text))
        if path is not None:
            with (info.folder / path).open('rb') as file:
                self.assertEqual(r.content, file.read(), url)
        return r

    def test_url_priority(self):
        self.check('/path/abc', text='/path/.*')
        self.check('/path/file', text='/path/file')
        self.check('/path/dir', text='/path/.*')
        self.check('/path/dir/', text='/path/dir/.*')
        self.check('/path/dir/abc', text='/path/dir/.*')
        self.check('/path/dir/file', text='/path/dir/file')
        self.check('/path/priority', text='/path/priority')


class TestDirectoryHandler(TestGramex):
    'Test gramex.handlers.DirectoryHandler'

    def test_directory(self):
        'Test DirectoryHandler'
        def adds_slash(url, check):
            self.assertFalse(url.endswith('/'), 'redirect_with_slash url must not end with /')
            r = self.get(url)
            if check:
                self.assertTrue(r.url.endswith('/'), url)
                self.assertIn(r.history[0].status_code, (301, 302), url)
            else:
                self.assertEqual(len(r.history), 0)

        self.check('/dir/noindex/', code=404)
        adds_slash('/dir/noindex/subdir', False)
        self.check('/dir/noindex/subdir/', code=404)
        self.check('/dir/noindex/index.html', path='dir/index.html')
        self.check('/dir/noindex/text.txt', path='dir/text.txt')
        self.check('/dir/noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/index/', code=200, text='subdir/</a>')
        adds_slash('/dir/index/subdir', True)
        self.check('/dir/index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/index/index.html', path='dir/index.html')
        self.check('/dir/index/text.txt', path='dir/text.txt')
        self.check('/dir/index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-present-index/', path='dir/index.html')
        adds_slash('/dir/default-present-index/subdir', True)
        self.check('/dir/default-present-index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/default-present-index/index.html', path='dir/index.html')
        self.check('/dir/default-present-index/text.txt', path='dir/text.txt')
        self.check('/dir/default-present-index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-missing-index/', code=200, text='subdir/</a>')
        adds_slash('/dir/default-missing-index/subdir', True)
        self.check('/dir/default-missing-index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/default-missing-index/index.html', path='dir/index.html')
        self.check('/dir/default-missing-index/text.txt', path='dir/text.txt')
        self.check('/dir/default-missing-index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-present-noindex/', path='dir/index.html')
        adds_slash('/dir/default-present-noindex/subdir', False)
        self.check('/dir/default-present-noindex/subdir/', code=404)
        self.check('/dir/default-present-noindex/index.html', path='dir/index.html')
        self.check('/dir/default-present-noindex/text.txt', path='dir/text.txt')
        self.check('/dir/default-present-noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-missing-noindex/', code=404)
        adds_slash('/dir/default-missing-noindex/subdir', False)
        self.check('/dir/default-missing-noindex/subdir/', code=404)
        self.check('/dir/default-missing-noindex/index.html', path='dir/index.html')
        self.check('/dir/default-missing-noindex/text.txt', path='dir/text.txt')
        self.check('/dir/default-missing-noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/noindex/binary.bin', path='dir/binary.bin')

        self.check('/dir/args/?x=1', text=json.dumps({'x': ['1']}))
        self.check('/dir/args/?x=1&x=2&y=3', text=json.dumps({'x': ['1', '2'], 'y': ['3']},
                                                             sort_keys=True))

    def test_transforms(self):
        with (info.folder / 'dir/markdown.md').open(encoding='utf-8') as f:
            self.check('/dir/transform/markdown.md', text=markdown.markdown(f.read()))

        handler = AttrDict(file=info.folder / 'dir/badgerfish.yaml')
        with (info.folder / 'dir/badgerfish.yaml').open(encoding='utf-8') as f:
            self.check('/dir/transform/badgerfish.yaml', text=badgerfish(f.read(), handler))
            self.check('/dir/transform/badgerfish.yaml', text='imported file')

    def test_default_config(self):
        'Check default gramex.yaml configuration'
        r = self.get('/reload-config', allow_redirects=False)
        self.assertIn(r.status_code, (301, 302), '/reload-config works and redirects')


class TestDataHandler(TestGramex):
    'Test gramex.handlers.DataHandler'
    database = 'sqlite'
    data = pd.read_csv(StringIO(
        """category,name,rating,votes
        Actors,Humphrey Bogart,0.57019677,109
        Actors,Cary Grant,0.438601513,142
        Actors,James Stewart,0.988373838,120
        Actors,Marlon Brando,0.102044811,108
        Actors,Fred Astaire,0.208876756,84
        Actresses,Katharine Hepburn,0.039187792,63
        Actresses,Bette Davis,0.282806963,14
        Actresses,Audrey Hepburn,0.120196561,94
        Actresses,Ingrid Bergman,0.296140198,52
        Actors,Spencer Tracy,0.466310773,192
        Actors,Charlie Chaplin,0.244425592,76"""), skipinitialspace=True)

    @classmethod
    def setUpClass(self):
        engine = sa.create_engine('sqlite:///tests/actors.db')
        self.data.to_sql('actors', con=engine, index=False)

    @classmethod
    def tearDownClass(self):
        os.remove('tests/actors.db')

    def test_pingdb(self):
        for frmt in ['csv', 'json', 'html']:
            self.check('/datastore/%s/%s/' % (self.database, frmt), code=200)
        self.check('/datastore/' + self.database + '/xyz', code=404)

    def test_fetchdb(self):
        base = self.base + '/datastore/' + self.database
        pdt.assert_frame_equal(self.data, pd.read_csv(base + '/csv/'))
        pdt.assert_frame_equal(self.data, pd.read_json(base + '/json/'))
        pdt.assert_frame_equal(self.data, pd.read_html(base + '/html/')[0]
                               .drop('Unnamed: 0', 1), check_less_precise=True)

    def test_querydb(self):
        def eq(a, b):
            return pdt.assert_frame_equal(a.reset_index(drop=True), b)

        def eqdt(a, b):
            return pdt.assert_frame_equal(a.reset_index(drop=True), b, check_dtype=False)

        # select, where, sort, offset, limit
        base = self.base + '/datastore/' + self.database + '/'
        eq(self.data[:5],
           pd.read_csv(base + 'csv/?_limit=5'))
        eq(self.data[5:],
           pd.read_csv(base + 'csv/?_offset=5'))
        eq(self.data.sort_values(by='votes'),
           pd.read_csv(base + 'csv/?_sort=asc:votes'))
        eq(self.data.sort_values(by='votes', ascending=False)[:5],
           pd.read_csv(base + 'csv/?_limit=5&_sort=desc:votes'))
        eq(self.data.sort_values(by=['category', 'name'], ascending=[False, False]),
           pd.read_csv(base + 'csv/?_sort=desc:category&_sort=desc:name'))
        eq(self.data[['name', 'votes']],
           pd.read_csv(base + 'csv/?_select=name&_select=votes'))
        eq(self.data.query('category=="Actors"'),
           pd.read_csv(base + 'csv/?_where=category==Actors'))
        eq(self.data.query('category!="Actors"'),
           pd.read_csv(base + 'csv/?_where=category!Actors'))
        eq(self.data[self.data.name.str.contains('Brando')],
           pd.read_csv(base + 'csv/?_where=name~Brando'))
        eq(self.data[~self.data.name.str.contains('Brando')],
           pd.read_csv(base + 'csv/?_where=name!~Brando'))
        eq(self.data.query('votes>100'),
           pd.read_csv(base + 'csv/?_where=votes>100'))
        eq(self.data.query('150 > votes > 100'),
           pd.read_csv(base + 'csv/?_where=votes<150&_where=votes>100&xyz=8765'))

        # Aggregation cases
        eqdt((self.data.groupby('category', as_index=False)
              .agg({'rating': max, 'votes': sum})
              .rename(columns={'rating': 'ratemax', 'votes': 'votesum'})),
             pd.read_csv(base + 'csv/?_groupby=category' +
                         '&_agg=ratemax:max(rating)&_agg=votesum:sum(votes)'))

        eqdt((self.data.query('120 > votes > 60')
              .groupby('category', as_index=False)
              .agg({'rating': max, 'votes': sum})
              .rename(columns={'rating':'ratemax', 'votes':'votesum'})
              .sort_values(by='votesum', ascending=True)),
             pd.read_csv(base + 'csv/?_groupby=category' +
                         '&_agg=ratemax:max(rating)&_agg=votesum:sum(votes)' +
                         '&_where=votes<120&_where=votes>60&_sort=asc:votesum'))

        eqdt((self.data.query('120 > votes > 60')
              .groupby('category', as_index=False)
              .agg({'rating': max, 'votes': sum})
              .rename(columns={'rating':'ratemax', 'votes':'votesum'})
              .loc[1:, ['category', 'votesum']]),
             pd.read_csv(base + 'csv/?_groupby=category' +
                         '&_agg=ratemax:max(rating)&_agg=votesum:sum(votes)' +
                         '&_where=votes<120&_where=votes>60' +
                         '&_select=category&_select=votesum&_offset=1'))


class TestMysqlDataHandler(TestDataHandler):
    # The parent TestDataHandler executes test cases for sqlite;
    # This class overwrites few of it properties to test it in MySQL
    database = 'mysql'
    engine = sa.create_engine('mysql+pymysql://root@localhost/')
    @classmethod
    def setUpClass(self):
        try:
            self.engine.execute("CREATE DATABASE test_datahandler")
            self.engine.dispose()
            self.engine = sa.create_engine('mysql+pymysql://root@localhost/test_datahandler')
            self.data.to_sql('actors', con=self.engine, index=False)
        except sa.exc.OperationalError:
            raise SkipTest('Unable to connect to MySQL database')

    @classmethod
    def tearDownClass(self):
        self.engine.execute("DROP DATABASE test_datahandler")
        self.engine.dispose()


class TestPostgresDataHandler(TestDataHandler):
    database = 'postgresql'
    engine = sa.create_engine('postgresql://postgres@localhost/postgres')
    @classmethod
    def setUpClass(self):
        try:
            conn = self.engine.connect()
            conn.execute('commit')
            conn.execute('CREATE DATABASE test_datahandler')
            conn.close()
            self.engine = sa.create_engine('postgresql://postgres@localhost/test_datahandler')
            self.data.to_sql('actors', con=self.engine, index=False)
            self.engine.dispose()
        except sa.exc.OperationalError:
            raise SkipTest('Unable to connect to PostgreSQL database')

    @classmethod
    def tearDownClass(self):
        self.engine = sa.create_engine('postgresql://postgres@localhost/postgres')
        conn = self.engine.connect()
        conn.execute('commit')
        # Terminate all other sessions using the test_datahandler database
        conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='test_datahandler'")
        conn.execute('DROP DATABASE test_datahandler')
        conn.close()
        self.engine.dispose()


class TestBlazeDataHandler(TestDataHandler):
    'Test gramex.handlers.DataHandler'
    database = 'blazesqlite'

    def test_querydb(self):
        def eq(a, b):
            return pdt.assert_frame_equal(a.reset_index(drop=True), b)

        # select, where, sort, offset, limit
        base = self.base + '/datastore/' + self.database + '/'
        eq(self.data[:5],
           pd.read_csv(base + 'csv/?_limit=5'))
        eq(self.data[5:],
           pd.read_csv(base + 'csv/?_offset=5'))
        eq(self.data.sort_values(by='votes'),
           pd.read_csv(base + 'csv/?_sort=asc:votes'))
        eq(self.data.sort_values(by='votes', ascending=False)[:5],
           pd.read_csv(base + 'csv/?_limit=5&_sort=desc:votes'))
        eq(self.data.sort_values(by=['category', 'name'], ascending=[False, False]),
           pd.read_csv(base + 'csv/?_sort=desc:category&_sort=desc:name'))
        eq(self.data[['name', 'votes']],
           pd.read_csv(base + 'csv/?_select=name&_select=votes'))
        eq(self.data.query('category=="Actors"'),
           pd.read_csv(base + 'csv/?_where=category==Actors'))
        eq(self.data.query('category!="Actors"'),
           pd.read_csv(base + 'csv/?_where=category!Actors'))
        eq(self.data.query('votes>100'),
           pd.read_csv(base + 'csv/?_where=votes>100'))
        eq(self.data.query('150 > votes > 100'),
           pd.read_csv(base + 'csv/?_where=votes<150&_where=votes>100&xyz=8765'))

        # TODO like & notlike operators name~Brando  name!~Brando

        # Aggregation cases
        eq((self.data.groupby('category', as_index=False)
            .agg({'rating': max, 'votes': sum})
            .rename(columns={'rating': 'ratemax', 'votes': 'votesum'})),
           pd.read_csv(base + 'csv/?_groupby=category' +
                       '&_agg=ratemax:max(rating)&_agg=votesum:sum(votes)'))

        eq((self.data.query('120 > votes > 60')
            .groupby('category', as_index=False)
            .agg({'rating': max, 'votes': sum})
            .rename(columns={'rating':'ratemax', 'votes':'votesum'})
            .sort_values(by='votesum', ascending=True)),
           pd.read_csv(base + 'csv/?_groupby=category' +
                       '&_agg=ratemax:max(rating)&_agg=votesum:sum(votes)' +
                       '&_where=votes<120&_where=votes>60&_sort=asc:votesum'))

        eq((self.data.query('120 > votes > 60')
            .groupby('category', as_index=False)
            .agg({'rating': max, 'votes': sum})
            .rename(columns={'rating':'ratemax', 'votes':'votesum'})
            .loc[1:, ['category', 'votesum']]),
           pd.read_csv(base + 'csv/?_groupby=category' +
                       '&_agg=ratemax:max(rating)&_agg=votesum:sum(votes)' +
                       '&_where=votes<120&_where=votes>60' +
                       '&_select=category&_select=votesum&_offset=1'))


class TestBlazeMysqlDataHandler(TestMysqlDataHandler, TestBlazeDataHandler):
    'Test gramex.handlers.DataHandler'
    database = 'blazemysql'

    def test_querydb(self):
        TestBlazeDataHandler.test_querydb(self)
