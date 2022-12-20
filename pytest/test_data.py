import os
import gramex.data
import pandas as pd
import pytest
from itertools import product
from contextlib import contextmanager
from pandas.testing import assert_frame_equal as afe

import dbutils  # noqa

folder = os.path.dirname(os.path.abspath(__file__))
sales_file = os.path.join(folder, '..', 'tests', 'sales.xlsx')
sales_data: pd.DataFrame = gramex.cache.open(sales_file)


@contextmanager
def dataframe():
    yield {'url': sales_data.copy()}


@contextmanager
def sqlite():
    url = dbutils.sqlite_create_db('test_delete.db', sales=sales_data)
    yield {'url': url, 'table': 'sales'}
    dbutils.sqlite_drop_db('test_delete.db')


@contextmanager
def mysql():
    server = os.environ.get('MYSQL_SERVER', 'localhost')
    url = dbutils.mysql_create_db(server, 'test_filter', sales=sales_data)
    yield {'url': url, 'table': 'sales'}
    dbutils.mysql_drop_db(server, 'test_filter')


@contextmanager
def postgres():
    server = os.environ.get('POSTGRES_SERVER', 'localhost')
    url = dbutils.postgres_create_db(server, 'test_filter', sales=sales_data)
    yield {'url': url, 'table': 'sales'}
    dbutils.postgres_drop_db(server, 'test_filter')


setups = [dataframe, sqlite, mysql, postgres]
delete_args = [
    {'देश': ['भारत']},
    {'city': ['Hyderabad', 'Bangalore']},
    {'देश': ['भारत'], 'product': ['Crème']},
]


@pytest.mark.parametrize('args,setup', product(delete_args, setups))
def test_delete(args, setup):
    with setup() as kwargs:
        filter = None
        for key, vals in args.items():
            if filter is None:
                filter = sales_data[key].isin(vals)
            else:
                filter = filter & sales_data[key].isin(vals)
        count = gramex.data.delete(args=args, **kwargs)
        assert count == filter.sum()
        result = gramex.data.filter(**kwargs)
        expected = sales_data[~filter]
        afe(result.reset_index(drop=True), expected.reset_index(drop=True))


filtercols_args = [
    [
        'sales|Range',
        {'sales|min': [sales_data.sales.min()], 'sales|max': [sales_data.sales.max()]},
    ],
    [
        'sales|Min',
        {'sales|Min': [sales_data.sales.min()]},
    ],
    [
        'sales,growth|Max',
        {'sales|Max': [sales_data.sales.max()], 'growth|Max': [sales_data.growth.max()]},
    ],
    [
        'sales,growth|Range',
        {
            'sales|min': [sales_data.sales.min()],
            'sales|max': [sales_data.sales.max()],
            'growth|min': [sales_data.growth.min()],
            'growth|max': [sales_data.growth.max()],
        },
    ],
]


@pytest.mark.parametrize('args,setup', product(filtercols_args, setups))
def test_filtercols(args, setup):
    with setup() as kwargs:
        result = gramex.data.filtercols(args={'_c': [args[0]]}, **kwargs)
        expected = pd.DataFrame(args[1])
        afe(result[args[0]], expected)
