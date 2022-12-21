'''
Test utilities to create and drop databases.
'''
import os
import sqlalchemy as sa
from pytest import skip

folder = os.path.dirname(os.path.abspath(__file__))


def mysql_create_db(server, database, **tables):
    url = 'mysql+pymysql://root@%s/' % server
    engine = sa.create_engine(url + '?charset=utf8', encoding='utf-8')
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
    engine = sa.create_engine(url, encoding='utf-8')
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