# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import gramex.cache
import pandas as pd
from nose.tools import eq_, ok_
from pandas.util.testing import assert_frame_equal as afe
from . import TestGramex, folder


class TestFilterHandler(TestGramex):
    sales_file = os.path.join(folder, 'sales.xlsx')
    sales = gramex.cache.open(sales_file, 'xlsx')
    census = gramex.cache.open(sales_file, 'xlsx', sheet_name='census')

    def test_filters(self):
        def eqframe(result, expected, **kwargs):
            '''Same as assert_frame_equal or afe, but does not compare index'''
            actual = pd.DataFrame(result)
            expected.index = actual.index
            afe(actual, expected, **kwargs)

        self.check('/filters/sales?_c=city')

        result = self.get('/filters/sales', params={'_c': ['city']}).json()
        expected = self.sales[['city']].drop_duplicates()
        eqframe(result['city'], expected, check_like=True)

        result = self.get('/filters/sales', params={'_c': ['city', 'product']}).json()
        expected_city = self.sales[['city']].drop_duplicates()
        expected_product = self.sales[['product']].drop_duplicates()
        eqframe(result['city'], expected_city, check_like=True)
        eqframe(result['product'], expected_product, check_like=True)

        limit = 10
        _args = {'_c': ['city'], '_limit': [limit]}
        result = self.get('/filters/sales', params=_args).json()
        actual = pd.DataFrame(result['city'])
        ok_(set(actual['city']).issubset(set(self.sales['city'].unique())))
        ok_(len(actual['city']) <= limit)

        _args = {'_c': ['city'], '_sort': ['city']}
        result = self.get('/filters/sales', params=_args).json()
        expected = self.sales[['city']].drop_duplicates().sort_values('city')
        eq_(set(result.keys()), {'city'})
        eqframe(result['city'], expected)

        # _args = {'_c': ['city'], '_sort': ['-city']}
        # result = self.get('/filters/sales', params=_args).json()
        # expected = self.sales.sort_values('sales', ascending=False)[['city']]
        # expected = expected.drop_duplicates().head(100)
        # eqframe(result['city'], expected)

        _args = {'_c': ['city'], '_sort': ['city', '-sales']}
        result = self.get('/filters/sales', params=_args).json()
        expected = self.sales.sort_values(['city', 'sales'], ascending=[True, False])
        expected = expected[['city']].drop_duplicates().head(100)
        eqframe(result['city'], expected)

        _args = {'_c': ['District'], 'State': ['KERALA']}
        result = self.get('/filters/census', params=_args).json()
        expected = self.census[self.census['State'] == 'KERALA'][['District']]
        expected = expected.drop_duplicates().head(100)
        eqframe(result['District'], expected)

        _args = {
            '_c': ['District', 'DistrictCaps'],
            '_sort': ['State', 'District'],
            'State': ['KERALA'],
            '_limit': [10],
        }
        result = self.get('/filters/census', params=_args).json()
        filtered = self.census.sort_values(['State', 'District'])
        filtered = filtered[filtered['State'] == 'KERALA']
        filtered_district = filtered[['District']].drop_duplicates().head(10)
        filtered_districtcaps = filtered[['DistrictCaps']].drop_duplicates().head(10)
        eqframe(result['District'], filtered_district)
        eqframe(result['DistrictCaps'], filtered_districtcaps)

        # _args = {
        #     '_c': ['DistrictCaps'],
        #     '_sort': ['State', 'District'],
        #     'State': ['KERALA'],
        #     'District>~': ['K'],
        #     '_limit': [10],
        # }
        # result = self.get('/filters/census', params=_args).json()
        # filtered = self.census.sort_values(['State', 'District'])
        # filtered = filtered[filtered['State'] == 'KERALA']
        # filtered = filtered[filtered['District'] >= 'K']
        # filtered = filtered[['DistrictCaps']].drop_duplicates().head(10)
        # eqframe(result['DistrictCaps'], filtered)

        _args = {'_c': ['city'], 'देश': ['भारत']}
        result = self.get('/filters/sales', params=_args).json()
        expected = self.sales[self.sales['देश'] == 'भारत'][['city']]
        expected = expected.drop_duplicates().head(100)
        eqframe(result['city'], expected)

        _args = {'_c': ['product'], 'देश': ['भारत']}
        result = self.get('/filters/sales', params=_args).json()
        expected = self.sales[self.sales['देश'] == 'भारत'][['product']]
        expected = expected.drop_duplicates().head(100)
        eqframe(result['product'], expected)
