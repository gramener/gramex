import os
import json
import random
import tornado
import datetime
import sqlalchemy
from urllib import urlencode
from passlib.hash import sha256_crypt


def create_user_database(url, table, user, password, salt):
    # Connect to the SQLAlchemy engine specified at url.
    # For example, this could be sqlite:///auth.db
    engine = sqlalchemy.create_engine(url, encoding='utf-8')

    # In the Gramex guide, we're using an sqlite3 database which is a file.
    # If the target folder doesn't exist, make sure we create it.
    folder = os.path.dirname(os.path.abspath(engine.url.database))
    if not os.path.exists(folder):
        os.makedirs(folder)

    # This method re-creates the user table each time. So drop it and create it.
    # Usually, you'd just use 'CREATE TABLE IF NOT EXISTS' or its equivalent.
    # The table must have:
    #   a column for the username (typically called user)
    #   a column for the password (typically called password)
    #   and any other optional columns (here, we're adding a string called role)
    engine.execute('DROP TABLE IF EXISTS %s' % table)
    engine.execute('CREATE TABLE %s (%s text, %s text, role)' %
                   (table, user, password))

    # Add all the users, encrypted passwords, and a role string.
    # We're using sha256_crypt as the password hash.
    # See the passlib documentation for details.
    engine.execute('INSERT INTO %s VALUES (?, ?, ?)' % table, [
        ['alpha', sha256_crypt.encrypt('alpha', salt=salt), 'admin manager'],
        ['beta', sha256_crypt.encrypt('beta', salt=salt), 'manager employee'],
        ['gamma', sha256_crypt.encrypt('gamma', salt=salt), 'employee'],
        ['delta', sha256_crypt.encrypt('delta', salt=salt), None],
    ])


def store_value(handler):
    handler.session.setdefault('randkey', random.randint(0, 1000))
    return json.dumps(handler.session, indent=4)


async_http_client = tornado.httpclient.AsyncHTTPClient()


@tornado.gen.coroutine
def contacts(handler):
    days = int(handler.get_argument('days', '30'))
    start = (datetime.datetime.today() - datetime.timedelta(days=days))
    result = yield async_http_client.fetch(
        'https://www.google.com/m8/feeds/contacts/default/full?' + urlencode({
            'updated-min': start.strftime('%Y-%m-%dT%H:%M:%S'),
            'max-results': 500,
            'alt': 'json',
        }),
        headers={'Authorization': 'Bearer ' + handler.session.get('google_access_token', '')},
    )
    try:
        contacts = json.loads(result.body)['feed']
        data = {'contacts': contacts.get('entry', [])}
    except Exception as e:
        data = {'error': repr(e)}
    raise tornado.gen.Return(json.dumps(data, indent=4))
