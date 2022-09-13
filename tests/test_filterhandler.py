import os
import gramex.cache
import pandas as pd
from . import TestGramex, folder, afe


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

        def unique_of(data, cols):
            return data.groupby(cols).size().reset_index().drop(0, 1)

        self.check('/filters/sales?_c=city')

        result = self.get('/filters/sales', params={'_c': ['city']}).json()
        expected = unique_of(self.sales, 'city')
        eqframe(result['city'], expected, check_like=True)

        result = self.get('/filters/sales', params={'_c': ['city', 'product']}).json()
        for col in ['city', 'product']:
            expected_col = unique_of(self.sales, col)
            eqframe(result[col], expected_col, check_like=True)

        limit = 10
        _args = {'_c': ['city'], '_limit': [limit]}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, 'city').head(limit)
        eqframe(result['city'], expected, check_like=True)

        _args = {'_c': ['city'], '_sort': ['city']}
        result = self.get('/filters/sales', params=_args).json()
        expected = unique_of(self.sales, 'city').sort_values('city')
        eqframe(result['city'], expected)

        # _args = {'_c': ['city'], '_sort': ['-city']}
        # result = self.get('/filters/sales', params=_args).json()
        # expected = self.sales.sort_values('sales', ascending=False)[['city']]
        # expected = expected.drop_duplicates().head(100)
        # eqframe(result['city'], expected)

        _args = {'_c': ['city'], '_sort': ['city', '-sales']}
        result = self.get('/filters/sales', params=_args).json()
        expected = self.sales.sort_values(['city', 'sales'], ascending=[True, False])
        expected = unique_of(self.sales, 'city')
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
        filtered = self.census.sort_values(['State', 'District'])
        filtered = filtered[filtered['State'] == 'KERALA']
        for col in ['District', 'DistrictCaps']:
            eqframe(result[col], unique_of(filtered, col).head(10))

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

        for col in ['city', 'product']:
            _args = {'_c': [col], 'देश': ['भारत']}
            result = self.get('/filters/sales', params=_args).json()
            expected = self.sales[self.sales['देश'] == 'भारत']
            expected = unique_of(expected, col)
            eqframe(result[col], expected)
