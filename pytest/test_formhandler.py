import os
import pytest
import gramex.data
import gramex.cache
from itertools import product
from contextlib import contextmanager
import pandas as pd
import dbutils
from pandas.testing import assert_frame_equal as afe
import json


folder = os.path.dirname(os.path.abspath(__file__))
sales_join_file = os.path.join(folder, "..", "tests", "sales_join.xlsx")
sales_join_data: pd.DataFrame = gramex.cache.open(sales_join_file, sheet_name="sales")
customers_data: pd.DataFrame = gramex.cache.open(sales_join_file, sheet_name="customers")
products_data: pd.DataFrame = gramex.cache.open(sales_join_file, sheet_name="products")

results = [{
    "kwargs" : {
      "url": "",
      "table": "sales",
    },
    "expected": "SELECT * FROM sales",
    "formatting": {
        "sale_date": pd.Timestamp,
    }
},{
    "kwargs" : {
        "url": "",
        "table": "sales",
        "join": json.dumps({
            "products": {
                "type": "inner",
                "column": {"products.id": "sales.product_id"},
            },
            "customers": {
                "type": "left",
                "column": {"sales.customer_id": "customers.id"},
            },
        }),
    },
    "expected": """
      SELECT
        sales.id              AS sales_id,
        sales.customer_id     AS sales_customer_id,
        sales.product_id      AS sales_product_id,
        sales.sale_date       AS sales_sale_date,
        sales.amount          AS sales_amount,
        sales.city            AS sales_city,
        products.id           AS sales_id,
        products.name         AS sales_name,
        products.price        AS sales_price,
        products.manufacturer AS sales_manufacturer,
        customers.id          AS sales_id,
        customers.name        AS sales_name,
        customers.city        AS sales_city       
      FROM sales
      JOIN products ON products.id==sales.product_id
      LEFT OUTER JOIN customers ON sales.customer_id==customers.id
    """,
    "formatting": {
        "sales_sale_date": pd.Timestamp,
    }
# },{
#     "kwargs" : {
#         "url": "",
#         "table": "sales",
#         "join": json.dumps({
#             "products": {
#                 "type": "inner",
#             },
#             "customers": {},
#         }),
#     },
#     "expected": 4,
}]

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


@pytest.mark.parametrize("result,db_setup", product(results, db_setups))
def test_formhandler_join(result, db_setup):
    kwargs = result["kwargs"]
    with db_setup() as url:
        kwargs["url"] = url
        actual = gramex.data.filter(args=[], meta={}, **kwargs)
        expected = pd.read_sql(result["expected"], url)
        for k, v in result["formatting"].items():
            expected[k] = expected[k].apply(v)
        afe(expected, actual)
