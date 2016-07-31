import os.path
import logging
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import DatabaseError


def data():
    """
    fetch flags data and create database.sqlite3 in this folder
    """
    url = 'https://gramener.com/flags/test.csv'
    folder = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(folder, 'database.sqlite3')
    engine = create_engine('sqlite:///%s' % filepath, encoding='utf-8')
    try:
        flags = pd.read_sql_table('flags', engine)
        assert len(flags) > 1
        logging.info('database.sqlite3 has flags table with data')
        return
    except DatabaseError:
        # If the database is corrupted, delete it
        os.unlink(filepath)
    except Exception:
        pass

    flags = pd.read_csv(url, encoding='cp1252')
    flags.to_sql('flags', engine, index=False)
    logging.info('database.sqlite3 created with flags table')


def bigint(content):
    for k, v in content.items():
        if k == 'c2':
            v = int(v)
            content[k] = v * v
    return content
