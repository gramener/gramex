import os
import json
import random
import sqlalchemy


def store_value(handler):
    handler.session.setdefault('randkey', random.randint(0, 1000))
    return json.dumps(handler.session, indent=4)


def create_user_database(url, table, user, password, salt):
    engine = sqlalchemy.create_engine(url, encoding='utf-8')
    folder = os.path.dirname(os.path.abspath(engine.url.database))
    if not os.path.exists(folder):
        os.makedirs(folder)
    engine.execute('CREATE TABLE IF NOT EXISTS %s (%s text, %s text, role)' %
                   (table, user, password))
    result = engine.execute('SELECT * FROM %s LIMIT 1' % table)
    if not result.fetchone():
        engine.execute('INSERT INTO %s VALUES (?, ?, ?)' % table, [
            ['alpha', 'alpha' + salt, 'admin manager'],
            ['beta', 'beta' + salt, 'manager employee'],
            ['gamma', 'gamma' + salt, 'employee'],
            ['delta', 'delta' + salt, None],
        ])
