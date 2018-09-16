import os
import json
import random
import tornado
import datetime
import sqlalchemy
import pandas as pd
from gramex.config import str_utf8, CustomJSONEncoder
from passlib.hash import sha256_crypt
from six.moves.urllib.parse import urlencode


def create_user_database(url, table, user, password, salt, excel):
    # Connect to the SQLAlchemy engine specified at url.
    # For example, this could be sqlite:///auth.db
    engine = sqlalchemy.create_engine(url, encoding=str_utf8)

    # In the Gramex guide, we're using an sqlite3 database and Excel file.
    # If the target folder doesn't exist, make sure we create it.
    for path in (engine.url.database, excel):
        folder = os.path.dirname(os.path.abspath(path))
        if not os.path.exists(folder):
            os.makedirs(folder)

    # This method re-creates the user table each time.
    # The table must have:
    #   a column for the username (typically called user)
    #   a column for the password (typically called password)
    #   and any other optional columns (here, we're adding email and role)
    # We're using sha256_crypt as the password hash.
    # Email IDs used are gramex.guide+alpha@gmail.com, gramex.guide+beta@gmail.com, etc
    email = 'gramex.guide+%s@gmail.com'
    data = pd.DataFrame([
        ['alpha', sha256_crypt.encrypt('alpha', salt=salt), email % 'alpha', 'admin manager'],
        ['beta', sha256_crypt.encrypt('beta', salt=salt), email % 'beta', 'manager employee'],
        ['gamma', sha256_crypt.encrypt('gamma', salt=salt), email % 'gamma', 'employee'],
        ['delta', sha256_crypt.encrypt('delta', salt=salt), email % 'delta', None],
    ], columns=[user, password, 'email', 'role'])
    data.to_sql(table, engine, index=False, if_exists='replace')
    data.to_excel(excel, index=False)   # noqa - encoding not required


def store_value(handler):
    handler.session.setdefault('randkey', random.randint(0, 1000))
    return json.dumps(handler.session, indent=4, cls=CustomJSONEncoder)


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


def signup_validate(handler, args):
    # TODO Nikhil: Provide Sample validation
    # What if user return dict/list/tuple?
    return False
