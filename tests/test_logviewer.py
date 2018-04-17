# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
        for transform in spec.kwargs.transforms:
            logviewer.apply_transform(cls.df, transform)

    def test_setup(self):
        # check if db exists
        ok_(os.path.isfile(self.dbpath))
        engine = sa.create_engine('sqlite:///{}'.format(self.dbpath))
        # check if db has 3 tables
        eq_(engine.table_names(), ['aggD', 'aggM', 'aggW'])

    def test_endpoints(self):
        self.check('/logviewer/')
        self.check('/logviewer/query/', code=404)
        # check query endpoints
        spec = self.get_keywith(conf.url, 'apps/logviewer/query-')
        base = '/logviewer/query/aggD'
        df = self.df
        # check filters
        for col in ['status', 'ip']:
            eq_(self.get('{}/filter{}/'.format(base, col)).json(),
                [{col: x} for x in sorted(df[col].unique())]
                )
        eq_(self.get('{}/filter{}/'.format(base, 'users')).json(),
            [{'user.id': x} for x in
             sorted(df[df['user.id_1'].eq(1)]['user.id'].unique())]
            )
        eq_(self.get('{}/filter{}/'.format(base, 'uri')).json(),
            (df[df['uri_1'].eq(1)]['uri'].value_counts()
             .astype(int)
             .rename_axis('uri').reset_index(name='views')
             .sort_values(by=['views', 'uri'], ascending=[False, True])[:100]
             .to_dict('r'))
            )
        # check KPIs
        eq_(self.get('{}/kpi-{}/'.format(base, 'pageviews')).json(),
            [{'value': len(df.index)}]
            )
        eq_(self.get('{}/kpi-{}/'.format(base, 'sessions')).json(),
            [{'value': df['new_session'].sum()}]
            )
        eq_(self.get('{}/kpi-{}/'.format(base, 'users')).json(),
            [{'value': df[df['user.id_1'].eq(1)]['user.id'].nunique()}]
            )
        eq_(self.get('{}/kpi-{}/'.format(base, 'urls')).json(),
            [{'value': df[df['uri_1'].eq(1)]['uri'].nunique()}]
            )
        r = self.get('{}/kpi-{}/'.format(base, 'avgtimespent')).json()
        aae(r[0]['value'],
            df['session_time'].sum() / df['new_session'].sum(),
            4)
        r = self.get('{}/kpi-{}/'.format(base, 'avgloadtime')).json()
        aae(r[0]['value'], df['duration'].mean(), 4)
        # check top10
        topten = [{'col': 'user.id', 'url': 'users', 'flag': True},
                  {'col': 'ip', 'url': 'ip'},
                  {'col': 'status', 'url': 'status'},
                  {'col': 'uri', 'url': 'uri', 'flag': True}]
        for top in topten:
            cond = (df[top['col'] + '_1'].eq(1)
                    if top.get('flag') else slice(None))
            eq_(self.get('{}/topten{}/'.format(base, top['url'])).json(),
                (df[cond][top['col']].value_counts()
                .astype(int)
                .rename_axis(top['col']).reset_index(name='views')
                .sort_values(by=['views', top['col']],
                             ascending=[False, True])[:10]
                .to_dict('r'))
                )
        # check trend
        eq_(self.get('{}/{}/'.format(base, 'pageviewstrend')).json(),
            (logviewer.pdagg(
                df[df['uri_1'].eq(1)],
                [{'key': 'time', 'freq': 'D'}],
                {'duration': ['count']})
            .assign(time=lambda x: x.time.dt.strftime('%Y-%m-%d 00:00:00'),
                    pageviews=lambda x: x.duration_count.astype(int))
            .drop('duration_count', 1)
            .query('pageviews != 0')
            .to_dict('r'))
            )
        eq_(self.get('{}/{}/'.format(base, 'sessionstrend')).json(),
            (logviewer.pdagg(
                df,
                [{'key': 'time', 'freq': 'D'}],
                {'new_session': ['sum']})
            .assign(time=lambda x: x.time.dt.strftime('%Y-%m-%d 00:00:00'),
                    sessions=lambda x: x.new_session_sum.astype(int))
            .drop('new_session_sum', 1)
            .query('sessions != 0')
            .to_dict('r'))
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
