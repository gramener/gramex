'''
Test utilities to create and drop databases.
Used by test_datahandler.py, test_queryhandler.py, ../testlib/
'''
from __future__ import unicode_literals

import os
import sqlalchemy as sa
from nose.plugins.skip import SkipTest
from gramex.config import str_utf8

folder = os.path.dirname(os.path.abspath(__file__))


def mysql_create_db(server, db, **tables):
    url = 'mysql+pymysql://root@%s/' % server
    engine = sa.create_engine(url + '?charset=utf8', encoding=str_utf8)
    try:
        engine.connect()
    except sa.exc.OperationalError:
        raise SkipTest('Unable to connect to %s' % url)
    engine.execute("DROP DATABASE IF EXISTS %s" % db)
    engine.execute("CREATE DATABASE %s CHARACTER SET utf8 COLLATE utf8_general_ci" % db)
    engine.dispose()
    engine = sa.create_engine(url + db + '?charset=utf8', encoding=str_utf8)
    for table_name, data in tables.items():
        data.to_sql(table_name, con=engine, index=False)
    engine.dispose()
    return url + db + '?charset=utf8'


def mysql_drop_db(server, db):
    url = 'mysql+pymysql://root@%s/' % server
    engine = sa.create_engine(url, encoding=str_utf8)
    engine.execute("DROP DATABASE IF EXISTS %s" % db)
    engine.dispose()


def postgres_create_db(server, db, **tables):
    url = 'postgresql://postgres@%s/' % server
    engine = sa.create_engine(url, encoding=str_utf8)
    try:
        conn = engine.connect()
    except sa.exc.OperationalError:
        raise SkipTest('Unable to connect to %s' % url)
    conn.execute('commit')
    conn.execute('DROP DATABASE IF EXISTS %s' % db)
    conn.execute('commit')
    conn.execute("CREATE DATABASE %s ENCODING 'UTF8'" % db)
    conn.close()
    engine = sa.create_engine(url + db, encoding=str_utf8)
    for table_name, data in tables.items():
        if '.' in table_name:
            schema, table_name = table_name.rsplit('.', 1)
            engine.execute('CREATE SCHEMA %s' % schema)
            data.to_sql(table_name, con=engine, schema=schema, index=False)
        else:
            data.to_sql(table_name, con=engine, index=False)
    return url + db


def postgres_drop_db(server, db):
    url = 'postgresql://postgres@%s/' % server
    engine = sa.create_engine(url, encoding=str_utf8)
    conn = engine.connect()
    conn.execute('commit')
    # Terminate all other sessions using the test_datahandler database
    conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                 "WHERE datname='%s'" % db)
    conn.execute('commit')
    conn.execute('DROP DATABASE IF EXISTS %s' % db)
    conn.execute('commit')
    conn.close()
    engine.dispose()


def sqlite_create_db(db, **tables):
    path = os.path.join(folder, db)
    if os.path.exists(path):
        os.unlink(path)
    url = 'sqlite:///' + path
    engine = sa.create_engine(url, encoding=str_utf8)
    for table_name, data in tables.items():
        data.to_sql(table_name, con=engine, index=False)
    return url


def sqlite_drop_db(db):
    path = os.path.join(folder, db)
    if os.path.exists(path):
        os.unlink(path)
