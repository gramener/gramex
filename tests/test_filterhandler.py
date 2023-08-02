import os
import gramex.cache
import pandas as pd
from nose.tools import eq_
from . import TestGramex, folder, afe


def eqframe(result, expected, **kwargs):
    '''Same as assert_frame_equal or afe, but does not compare index'''
    actual = pd.DataFrame(result)
    expected.index = actual.index
    afe(actual, expected, **kwargs)


def unique_of(data: pd.DataFrame, cols):
    return data.groupby(cols).size().reset_index().drop(0, axis=1)


class TestFilterHandler(TestGramex):
    sales_file = os.path.join(folder, 'sales.xlsx')
    sales = gramex.cache.open(sales_file, 'xlsx')
    census = gramex.cache.open(sales_file, 'xlsx', sheet_name='census')

    def test_filters(self):
        self.check('/filters/sales?_c=city')

        result = self.get('/filters/sales', params={'_c': ['city']}).json()
        expected = unique_of(self.sales, 'city')
        eqframe(result['city'], expected)

        result = self.get('/filters/sales', params={'_c': ['city', 'product']}).json()
        for col in ['city', 'product']:
            expected_col = unique_of(self.sales, col)
            eqframe(result[col], expected_col)

        limit = 10
        _args = {'_c': ['city'], '_limit': [limit]}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, 'city').head(limit)
        eqframe(result['city'], expected)

        _args = {'_c': ['city'], '_sort': ['city']}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, 'city').sort_values('city')
        eqframe(result['city'], expected)

        _args = {'_c': ['city'], '_sort': ['city', '-sales']}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(expected, 'city')
        expected = expected.sort_values(['city'])  # sales is ignored. It sorts AFTER grouping
        eqframe(result['city'], expected)

        _args = {'_c': ['District'], 'State': ['KERALA']}
        result = self.get('/filters/census', params=_args).json()
        expected = self.census[self.census['State'] == 'KERALA']
        expected = unique_of(expected, 'District')
        eqframe(result['District'], expected)

        _args = {
            '_c': ['District', 'DistrictCaps'],
            '_sort': ['State', 'District'],
            'State': ['KERALA'],
            '_limit': [10],
        }
        result = self.get('/filters/census', params=_args).json()
        filtered = self.census[self.census['State'] == 'KERALA']
        for col, sort_cols in [('District', ['District']), ('DistrictCaps', [])]:
            eqframe(result[col], unique_of(filtered, col).sort_values(sort_cols).head(10))

        for col in ['city', 'product']:
            _args = {'_c': [col], 'देश': ['भारत']}
            result = self.get('/filters/sales', params=_args).json()
            expected = self.sales[self.sales['देश'] == 'भारत']
            expected = unique_of(expected, col)
            eqframe(result[col], expected)

    def test_ranges(self):
        sales, growth = self.sales.sales, self.sales.growth
        result = self.get('/filters/sales', params={'_c': ['sales|Range']}).json()
        expected = {'sales|Range': [{'sales|min': sales.min(), 'sales|max': sales.max()}]}
        eq_(result, expected)

        result = self.get('/filters/sales', params={'_c': ['sales|Min']}).json()
        expected = {'sales|Min': [{'sales|Min': sales.min()}]}
        eq_(result, expected)

        result = self.get('/filters/sales', params={'_c': ['sales,growth|Max']}).json()
        expected = {'sales,growth|Max': [{'sales|Max': sales.max(), 'growth|Max': growth.max()}]}
        eq_(result, expected)

        result = self.get('/filters/sales', params={'_c': ['sales,growth|Range']}).json()
        expected = {
            'sales,growth|Range': [
                {
                    'sales|min': sales.min(),
                    'sales|max': sales.max(),
                    'growth|min': growth.min(),
                    'growth|max': growth.max(),
                }
            ]
        }
        eq_(result, expected)

    def test_multifilters(self):
        _args = {'_c': ['देश,city']}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, ['देश', 'city'])
        eqframe(result['देश,city'], expected)

        _args = {'_c': ['city,city']}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, ['city'])
        eqframe(result['city,city'], expected)

        _args = {'_c': ['देश,city,product']}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, ['देश', 'city', 'product'])
        eqframe(result['देश,city,product'], expected)

        _args = {'_c': ['देश,city', 'product']}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, ['देश', 'city'])
        eqframe(result['देश,city'], expected)
        expected = unique_of(self.sales, ['product'])
        eqframe(result['product'], expected)

        limit = 10
        _args = {'_c': ['देश,city'], '_limit': limit}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, ['देश', 'city']).head(limit)
        eqframe(result['देश,city'], expected)

        _args = {'_c': ['देश,city'], '_sort': ['देश', '-city']}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, ['देश', 'city']).sort_values(
            ['देश', 'city'], ascending=[True, False]
        )
        eqframe(result['देश,city'], expected)

        _args = {'_c': ['देश,city'], '_sort': ['देश', '-sales']}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, ['देश', 'city'])
        expected = expected.sort_values(['देश'])
        eqframe(result['देश,city'], expected)

        _args = {'_c': ['देश,city'], 'sales>': ['500']}
        result = self.get('/filters/sales', params=_args).json()
        expected = self.sales[self.sales['sales'] > 500]
        expected = unique_of(expected, ['देश', 'city'])
        eqframe(result['देश,city'], expected)

        _args = {'_c': ['देश,city'], 'sales>': ['500'], 'growth>': ['0'], '_sort': ['city']}
        result = self.get('/filters/sales', params=_args).json()
        expected = self.sales[(self.sales['sales'] > 500) & (self.sales['growth'] > 0)]
        expected = unique_of(expected, ['देश', 'city']).sort_values(['city'])
        eqframe(result['देश,city'], expected)
