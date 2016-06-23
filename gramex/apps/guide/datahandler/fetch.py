import os.path
import logging
import pandas as pd
from sqlalchemy import create_engine


def data():
    """
    fetch flags data and create database.sqlite3 in this folder
    """
    url = 'https://gramener.com/flags/test.csv'
    folder = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(folder, 'database.sqlite3')

    if os.path.exists(filepath):
        logging.info('database.sqlite3 already present')
        return

    logging.info('fetch flags data and create database.sqlite3')
    flags = pd.read_csv(url, encoding='cp1252')
    engine = create_engine('sqlite:///%s' % filepath, encoding='utf-8')
    flags.to_sql('flags', engine, index=False)

def bigint(val):
    return int(val) * 10
