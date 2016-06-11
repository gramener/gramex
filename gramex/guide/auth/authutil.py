import os
import json
import random
import sqlalchemy
from passlib.hash import sha256_crypt

def store_value(handler):
    handler.session.setdefault('randkey', random.randint(0, 1000))
    return json.dumps(handler.session, indent=4)


def create_user_database(url, table, user, password, salt):
    engine = sqlalchemy.create_engine(url, encoding='utf-8')
    folder = os.path.dirname(os.path.abspath(engine.url.database))
    if not os.path.exists(folder):
        os.makedirs(folder)
    engine.execute('DROP TABLE %s' % table)
    engine.execute('CREATE TABLE %s (%s text, %s text, role)' %
                   (table, user, password))
    result = engine.execute('SELECT * FROM %s LIMIT 1' % table)
    if not result.fetchone():
        engine.execute('INSERT INTO %s VALUES (?, ?, ?)' % table, [
            ['alpha', sha256_crypt.encrypt('alpha', salt=salt), 'admin manager'],
            ['beta', sha256_crypt.encrypt('beta', salt=salt), 'manager employee'],
            ['gamma', sha256_crypt.encrypt('gamma', salt=salt), 'employee'],
            ['delta', sha256_crypt.encrypt('delta', salt=salt), None],
        ])
