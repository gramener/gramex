import os
import gramex.data
import pandas as pd
from pandas.testing import assert_frame_equal as afe

folder = os.path.dirname(os.path.abspath(__file__))


class TestFilterCols:
    sales_file = os.path.join(folder, '..', 'tests', 'sales.xlsx')
    sales_data = gramex.cache.open(sales_file)

    def test_agg(self):
        #
        sales, growth = self.sales_data.sales, self.sales_data.growth
        result = gramex.data.filtercols(self.sales_file, args={'_c': ['sales|Range']})
        expected = pd.DataFrame({'sales|min': [sales.min()], 'sales|max': [sales.max()]})
        afe(result['sales|Range'], expected)

        result = gramex.data.filtercols(self.sales_file, args={'_c': ['sales|Min']})
        expected = pd.DataFrame({'sales|Min': [sales.min()]})
        afe(result['sales|Min'], expected)

        result = gramex.data.filtercols(self.sales_file, args={'_c': ['sales,growth|Max']})
        expected = pd.DataFrame({'sales|Max': [sales.max()], 'growth|Max': [growth.max()]})
        afe(result['sales,growth|Max'], expected)

        result = gramex.data.filtercols(self.sales_file, args={'_c': ['sales,growth|Range']})
        expected = pd.DataFrame(
            {
                'sales|min': [sales.min()],
                'sales|max': [sales.max()],
                'growth|min': [growth.min()],
                'growth|max': [growth.max()],
            }
        )
        afe(result['sales,growth|Range'], expected)
