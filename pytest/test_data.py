import os
import gramex.data
import pandas as pd
import pytest
from itertools import product
from contextlib import contextmanager
from pandas.testing import assert_frame_equal as afe

import utils  # noqa

folder = os.path.dirname(os.path.abspath(__file__))
sales_file = os.path.join(folder, '..', 'tests', 'sales.xlsx')
sales_data: pd.DataFrame = gramex.cache.open(sales_file, sheet_name='sales')
dates_data: pd.DataFrame = gramex.cache.open(sales_file, sheet_name='dates')


@contextmanager
def dataframe():
    yield {'url': sales_data.copy()}


@contextmanager
def sqlite():
    url = utils.sqlite_create_db('test_delete.db', sales=sales_data, dates=dates_data)
    yield {'url': url, 'table': 'sales'}
    utils.sqlite_drop_db('test_delete.db')


@contextmanager
def mysql():
    server = os.environ.get('MYSQL_SERVER', 'localhost')
    url = utils.mysql_create_db(server, 'test_filter', sales=sales_data, dates=dates_data)
    yield {'url': url, 'table': 'sales'}
    utils.mysql_drop_db(server, 'test_filter')


@contextmanager
def postgres():
    server = os.environ.get('POSTGRES_SERVER', 'localhost')
    url = utils.postgres_create_db(server, 'test_filter', sales=sales_data, dates=dates_data)
    # Postgres needs a "ping" to connect to the database. So run a query and fetch 1 row.
    # Maybe related to https://stackoverflow.com/a/42546718/100904
    gramex.data.filter(url=url, table='sales', args={'_limit': [1]})
    yield {'url': url, 'table': 'sales'}
    utils.postgres_drop_db(server, 'test_filter')


db_setups = [dataframe, sqlite, mysql, postgres]
delete_args = [
    {'देश': ['भारत']},
    {'city': ['Hyderabad', 'Bangalore']},
    {'देश': ['भारत'], 'product': ['Crème']},
]


@pytest.mark.parametrize('args,db_setup', product(delete_args, db_setups))
def test_delete(args, db_setup):
    with db_setup() as kwargs:
        filter = None
        for key, vals in args.items():
            if filter is None:
                filter = sales_data[key].isin(vals)
            else:
                filter = filter & sales_data[key].isin(vals)
        meta = {}
        count = gramex.data.delete(args=args, meta=meta, **kwargs)
        # TODO: validate meta
        assert count == filter.sum()
        result = gramex.data.filter(**kwargs)
        expected = sales_data[~filter]
        afe(result.reset_index(drop=True), expected.reset_index(drop=True))


@contextmanager
def check_argstype_sales():
    query = '''
        SELECT * FROM {table}
        WHERE देश = :country
        AND city IN :cities
        AND product IN :products
        AND sales > :salesmin
    '''
    args = {
        'table': ['sales'],
        'country': ['भारत'],
        'cities': ['Hyderabad', 'Bangalore'],
        'products': ['Crème'],
        'salesmin': ['20'],
    }
    argstype = {
        'cities': {'type': str, 'expanding': True},
        'products': {'expanding': True},
        'salesmin': 'float',
    }
    expected = sales_data[
        (sales_data['देश'] == args['country'][0])
        & (sales_data['city'].isin(args['cities']))
        & (sales_data['product'].isin(args['products']))
        & (sales_data['sales'] > float(args['salesmin'][0]))
    ]
    yield query, args, argstype, expected


@contextmanager
def check_argstype_dates():
    query = '''
        SELECT * FROM {table}
        WHERE date BETWEEN :start AND :end
        AND sales > :salesmin
    '''
    args = {
        'table': ['dates'],
        'start': ['2018-01-01'],
        'end': ['31 Jan 2018 23:59:59'],
        'salesmin': ['20'],
    }
    argstype = {
        'start': 'date',
        'end': 'pd.to_datetime',
        'salesmin': 'int',
    }
    expected = dates_data[
        (dates_data['date'] >= pd.to_datetime(args['start'][0]))
        & (dates_data['date'] <= pd.to_datetime(args['end'][0]))
        & (dates_data['sales'] > int(args['salesmin'][0]))
    ]
    yield query, args, argstype, expected


argstype_args = [check_argstype_sales, check_argstype_dates]


@pytest.mark.parametrize(
    'args,db_setup',
    product(
        argstype_args,
        db_setups[1:],  # Only test with databases, not dataframes
    ),
)
def test_argstype(args, db_setup):
    with db_setup() as kwargs:
        with args() as (query, params, argstype, expected):
            meta = {}
            result = gramex.data.filter(
                args=params, meta=meta, argstype=argstype, query=query, **kwargs
            )
            # SQLite stores dates as strings. Convert these
            if 'date' in result.columns and not result['date'].dtype.name.startswith('date'):
                result['date'] = pd.to_datetime(result['date'])
            # TODO: Validate meta
            afe(result.reset_index(drop=True), expected.reset_index(drop=True))


filtercols_args = [
    {
        '_c': 'sales|Range',
        'out': {'sales|min': [sales_data.sales.min()], 'sales|max': [sales_data.sales.max()]},
    },
    {
        '_c': 'sales|Min',
        'out': {'sales|Min': [sales_data.sales.min()]},
    },
    {
        '_c': 'sales,growth|Max',
        'out': {'sales|Max': [sales_data.sales.max()], 'growth|Max': [sales_data.growth.max()]},
    },
    {
        '_c': 'sales,growth|Range',
        'out': {
            'sales|min': [sales_data.sales.min()],
            'sales|max': [sales_data.sales.max()],
            'growth|min': [sales_data.growth.min()],
            'growth|max': [sales_data.growth.max()],
        },
    },
]


@pytest.mark.parametrize('args,setup', product(filtercols_args, db_setups))
def test_filtercols(args, setup):
    with setup() as kwargs:
        result = gramex.data.filtercols(args={'_c': [args['_c']]}, **kwargs)
        expected = pd.DataFrame(args['out'])
        afe(result[args['_c']], expected)
