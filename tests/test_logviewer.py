import os.path
import pandas as pd
import gramex.cache
from glob import glob
import sqlalchemy as sa
from nose.tools import eq_, ok_
from nose.tools import assert_almost_equals as aae
from pandas.testing import assert_frame_equal as afe
from gramex import conf
from gramex.services import info
from gramex.apps.logviewer import logviewer
from . import TestGramex
import unittest


class TestLogViewer(TestGramex):

    @staticmethod
    def get_keywith(config, key):
        item = next((v for k, v in config.items()
                    if k.startswith(key)), None)
        return item

    @classmethod
    def setUpClass(cls):
        cls.log_file = conf.log.handlers.requests.filename
        cls.columns = conf.log.handlers.requests['keys']
        cls.dirpath = os.path.dirname(cls.log_file)
        cls.dbpath = os.path.join(cls.dirpath, 'logviewer.db')
        cls.queryconf = cls.get_keywith(conf.url, 'apps/logviewer/query-')
        schd = cls.get_keywith(info.schedule, 'apps/logviewer-')
        # check schedule is present in config
        ok_(schd is not None)
        # Remove logviewer.db before running scheduler
        os.remove(cls.dbpath)
        # run logviewer scheduler once
        schd.run()
        # df with raw logs
        df = pd.concat([
            gramex.cache.open(f, 'csv', names=cls.columns).fillna('-')
            for f in glob(cls.log_file + '*')
        ], ignore_index=True)
        cls.df = logviewer.prepare_logs(df)
        spec = cls.get_keywith(conf.schedule, 'apps/logviewer-')
        for transform_type in ['transforms', 'post_transforms']:
            for transform in spec.kwargs.get(transform_type, []):
                logviewer.apply_transform(cls.df, transform)

    def test_setup(self):
        # check if db exists
        ok_(os.path.isfile(self.dbpath))
        engine = sa.create_engine('sqlite:///{}'.format(self.dbpath))
        # check if db has 3 tables
        eq_(engine.table_names(), ['aggD', 'aggM', 'aggW'])

    @unittest.skip('Known failure.')
    def test_endpoints(self):
        self.check('/logviewer/')
        self.check('/logviewer/query/', code=404)
        # check query endpoints
        spec = self.get_keywith(conf.url, 'apps/logviewer/query-')
        base = '/logviewer/query/aggD'
        df = self.df
        df_user1 = df['user.id_1'].eq(1)
        df_uri1 = df['uri_1'].eq(1)
        # check filters
        for col in ['status', 'ip']:
            eq_(self.get('{}/filter{}/'.format(base, col)).json(),
                [{col: x} for x in sorted(df[col].unique().astype(str))]
                )
        eq_(self.get('{}/filter{}/?_limit=10000'.format(base, 'users')).json(),
            [{'user.id': x} for x in
             sorted(df[df_user1]['user.id'].unique())]
            )
        # ToDo: See https://github.com/gramener/gramex/issues/252
        ideal = df[df_uri1]['uri'].value_counts().astype(int)[:100]
        ideal = ideal.rename_axis('uri').reset_index(name='views')
        ideal = ideal.sort_values(by=['views', 'uri'], ascending=[False, True])
        ideal.reset_index(inplace=True, drop=True)
        actual = self.get('{}/filter{}/'.format(base, 'uri')).json()
        actual = pd.DataFrame.from_records(actual)
        actual.sort_values(by=['views', 'uri'], ascending=[False, True], inplace=True)
        actual.reset_index(inplace=True, drop=True)
        afe(actual, ideal)
        # check KPIs
        eq_(self.get('{}/kpi-{}/'.format(base, 'pageviews')).json(),
            [{'value': len(df[df_uri1].index)}]
            )
        eq_(self.get('{}/kpi-{}/'.format(base, 'sessions')).json(),
            [{'value': df[df_user1]['new_session'].sum()}]
            )
        eq_(self.get('{}/kpi-{}/'.format(base, 'users')).json(),
            [{'value': df[df_user1]['user.id'].nunique()}]
            )
        eq_(self.get('{}/kpi-{}/'.format(base, 'urls')).json(),
            [{'value': df[df_uri1]['uri'].nunique()}]
            )
        r = self.get('{}/kpi-{}/'.format(base, 'avgtimespent')).json()
        aae(r[0]['value'],
            df[df_user1]['session_time'].sum() / df[df_user1]['new_session'].sum(),
            4)
        r = self.get('{}/kpi-{}/'.format(base, 'avgloadtime')).json()
        aae(r[0]['value'], df['duration'].mean(), 4)
        # check top10
        topten = [{'col': 'user.id', 'url': 'users', 'values': 'views', 'flag': True},
                  {'col': 'ip', 'url': 'ip', 'values': 'requests'},
                  {'col': 'status', 'url': 'status', 'values': 'requests'},
                  {'col': 'uri', 'url': 'uri', 'values': 'views', 'flag': True}]
        for top in topten:
            cond = (df[top['col'] + '_1'].eq(1)
                    if top.get('flag') else slice(None))
            eq_(self.get('{}/topten{}/'.format(base, top['url'])).json(),
                (df[cond][top['col']].value_counts()
                .astype(int)
                .rename_axis(top['col']).reset_index(name=top['values'])
                .sort_values(by=[top['values'], top['col']],
                             ascending=[False, True])[:10]
                .to_dict('r'))
                )
        # check trend
        dff = logviewer.pdagg(df[df_uri1],
                              [{'key': 'time', 'freq': 'D'}],
                              {'duration': ['count']})
        dff['time'] = dff['time'].dt.strftime('%Y-%m-%d 00:00:00')
        dff['pageviews'] = dff['duration_count'].astype(int)
        dff = dff[dff['pageviews'].ne(0)]
        eq_(self.get('{}/{}/'.format(base, 'pageviewstrend')).json(),
            dff.drop('duration_count', 1).to_dict('r')
            )
        dff = logviewer.pdagg(df[df_user1],
                              [{'key': 'time', 'freq': 'D'}],
                              {'new_session': ['sum']})
        dff['time'] = dff['time'].dt.strftime('%Y-%m-%d 00:00:00')
        dff['sessions'] = dff['new_session_sum'].astype(int)
        dff = dff[dff['sessions'].ne(0)]
        eq_(self.get('{}/{}/'.format(base, 'sessionstrend')).json(),
            dff.drop('new_session_sum', 1).query('sessions != 0').to_dict('r')
            )
        # TODO trend queries
        for q in spec.kwargs.kwargs.queries.keys():
            if q.endswith('trend'):
                self.check('{}/{}/'.format(base, q))

    def test_pdagg(self):
        dfe = (self.df.groupby([pd.Grouper(key='time', freq='D')])
               .agg({'duration': ['count']}).reset_index())
        dfe.columns = ['time', 'duration_count']
        afe(logviewer.pdagg(
            self.df,
            [{'key': 'time', 'freq': 'D'}],
            {'duration': ['count']}),
            dfe
            )

    def test_prepare_where(self):
        eq_(logviewer.prepare_where(
            'SELECT * FROM tb', {'col1>': ['10']}, ['col1']),
            'WHERE "col1" > "10"')
        eq_(logviewer.prepare_where(
            'SELECT * FROM tb WHERE col2 > 1', {'col1>': ['10']}, ['col1']),
            'AND "col1" > "10"')
        eq_(logviewer.prepare_where(
            '', {'col1>': ['10']}, ['col1']),
            'WHERE "col1" > "10"')

    def test_apply_transform(self):
        ok_('__temp__' not in self.df)
        spec = {
            'type': 'derive',
            'expr': {'col': 'user.id', 'op': 'NOTIN', 'value': ['-', 'dev']},
            'as': '__temp__'
        }
        logviewer.apply_transform(self.df, spec)
        ok_('__temp__' in self.df)
        self.df.drop('__temp__', 1)
