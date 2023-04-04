import os
import pytest
import gramex.data
import gramex.cache
from itertools import product
from contextlib import contextmanager
import pandas as pd
import dbutils
from pandas.testing import assert_frame_equal as afe
from glob import glob


folder = os.path.dirname(os.path.abspath(__file__))
sales_join_file = os.path.join(folder, "..", "tests", "sales_join.xlsx")
sales_join_data: pd.DataFrame = gramex.cache.open(sales_join_file, sheet_name="sales")
customers_data: pd.DataFrame = gramex.cache.open(sales_join_file, sheet_name="customers")
products_data: pd.DataFrame = gramex.cache.open(sales_join_file, sheet_name="products")


@contextmanager
def sqlite():
    yield dbutils.sqlite_create_db(
        "test_delete.db",
        sales=sales_join_data,
        customers=customers_data,
        products=products_data,
    )
    dbutils.sqlite_drop_db("test_delete.db")


db_setups = [
    # dataframe,
    sqlite,
    # mysql,
    # postgres,
]


@pytest.mark.parametrize(
    "result,db_setup", product(glob(os.path.join(folder, "formhandler-*", "*.yaml")), db_setups)
)
def test_formhandler_join(result, db_setup):
    resJson = gramex.cache.open(result)
    kwargs, formatting = resJson["kwargs"], resJson["formatting"]
    args = []
    if 'args' in resJson:
        args = resJson['args']
    with db_setup() as url:
        kwargs["url"] = url
        expected = pd.read_sql(resJson["expected"], url)
        actual = gramex.data.filter(args=args, meta={}, **kwargs)
        for k, v in formatting.items():
            fun = getattr(pd, v)
            expected[k] = expected[k].apply(fun)
        afe(expected, actual)
