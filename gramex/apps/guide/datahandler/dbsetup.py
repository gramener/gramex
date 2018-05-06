import os.path
import pandas as pd
from gramex.config import app_log, str_utf8
from sqlalchemy import create_engine
from sqlalchemy.exc import DatabaseError

folder = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(folder, 'database.sqlite3')
engine = create_engine('sqlite:///%s' % filepath, encoding=str_utf8)


def flags():
    """
    fetch flags data into database.sqlite3/flags
    """
    try:
        flags = pd.read_sql_table('flags', engine)
        if len(flags) >= 1:
            return
    except DatabaseError:
        pass
    if os.path.exists(filepath):
        app_log.warning('database.sqlite3 corrupted. Removing it')
        os.unlink(filepath)
    url = os.path.join(folder, 'flags.csv')
    flags = pd.read_csv(url, encoding='cp1252')
    flags.to_sql('flags', engine, index=False)
    app_log.info('database.sqlite3 created with flags table')


def points():
    """generate random data into database.sqlite3/points"""
    pd.DataFrame({
        'x': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'y': [10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
    }).to_sql('points', engine, index=False, if_exists='replace')


def bigint(content):
    for k, v in content.items():
        if k == 'c2':
            v = int(v)
            content[k] = v * v
    return content
