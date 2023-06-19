'''
Test utilities to create and drop databases.
'''
import os
import requests
import sqlalchemy as sa
import time
from pytest import skip

folder = os.path.dirname(os.path.abspath(__file__))
info = {}


def gramex_port():
    '''Wait for Gramex to start on $GRAMEX_PORT. Return port number if it does, else None'''
    port = os.environ.get('GRAMEX_PORT', '9999')
    if 'gramex_started' in info:
        return port
    # Normally, we just need to wait for requests.get('localhost:9999').
    # But if Tornado binds to the port but hasn't started, requests returns an error.
    # So we wait for 1 second (100 times with a 0.01s delay) until Tornado starts.
    for x in range(10):
        try:
            r = requests.get(f'http://localhost:{port}', timeout=0.1)
            if r.status_code == 200:
                info['gramex_started'] = True
                return port
        except requests.exceptions.ConnectionError:
            time.sleep(0.01)
    return None


def mysql_create_db(server, database, **tables):
    url = 'mysql+pymysql://root@%s/' % server
    engine = sa.create_engine(
        f'{url}?charset=utf8', encoding='utf-8', connect_args={'connect_timeout': 1}
    )
    try:
        engine.connect()
    except sa.exc.OperationalError:
        skip('Unable to connect to %s' % url)
    engine.execute("DROP DATABASE IF EXISTS %s" % database)
    engine.execute("CREATE DATABASE %s CHARACTER SET utf8 COLLATE utf8_general_ci" % database)
    engine.dispose()
    engine = sa.create_engine(url + database + '?charset=utf8', encoding='utf-8')
    for table_name, data in tables.items():
        data.to_sql(table_name, con=engine, index=False)
    engine.dispose()
    return url + database + '?charset=utf8'


def mysql_drop_db(server, database):
    url = 'mysql+pymysql://root@%s/' % server
    engine = sa.create_engine(url, encoding='utf-8')
    engine.execute("DROP DATABASE IF EXISTS %s" % database)
    engine.dispose()


def postgres_create_db(server, database, **tables):
    url = 'postgresql://postgres@%s/' % server
    engine = sa.create_engine(url, encoding='utf-8', connect_args={'connect_timeout': 0.5})
    try:
        conn = engine.connect()
    except sa.exc.OperationalError:
        skip('Unable to connect to %s' % url)
    conn.execute('COMMIT')
    conn.execute('DROP DATABASE IF EXISTS %s' % database)
    conn.execute('COMMIT')
    conn.execute("CREATE DATABASE %s ENCODING 'UTF8'" % database)
    conn.close()
    engine = sa.create_engine(url + database, encoding='utf-8')
    for table_name, data in tables.items():
        if '.' in table_name:
            schema, table_name = table_name.rsplit('.', 1)
            engine.execute('CREATE SCHEMA %s' % schema)
            data.to_sql(table_name, con=engine, schema=schema, index=False)
        else:
            data.to_sql(table_name, con=engine, index=False)
    return url + database


def postgres_drop_db(server, database):
    url = 'postgresql://postgres@%s/' % server
    engine = sa.create_engine(url, encoding='utf-8')
    conn = engine.connect()
    conn.execute('COMMIT')
    # Terminate all other sessions using the test_datahandler database
    conn.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='%s'" % database
    )
    conn.execute('COMMIT')
    conn.execute('DROP DATABASE IF EXISTS %s' % database)
    conn.execute('COMMIT')
    conn.close()
    engine.dispose()


def sqlite_create_db(database, **tables):
    path = os.path.join(folder, database)
    if os.path.exists(path):
        os.unlink(path)
    url = 'sqlite:///' + path
    engine = sa.create_engine(url, encoding='utf-8')
    for table_name, data in tables.items():
        # sqlite limits SQLITE_MAX_VARIABLE_NUMBER to 999
        # Ensure # columns * chunksize < 999
        data.to_sql(table_name, con=engine, index=False, chunksize=100)
    return url


def sqlite_drop_db(database):
    path = os.path.join(folder, database)
    if os.path.exists(path):
        os.unlink(path)


def mongodb_create_db(url, database, **tables):
    import pymongo

    client = pymongo.MongoClient(url)
    db = client[database]
    for collection, data in tables.items():
        if len(data):
            db[collection].insert_many(data.to_dict('records'))


def mongodb_drop_db(url, database):
    import pymongo

    client = pymongo.MongoClient(url)
    client.drop_database(database)
