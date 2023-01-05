'''Migrate from older versions of Gramex'''
import os


def user_db():
    '''Migrate user auth database from gramex 1.86.1 to 1.87.0.

    Till gramex 1.86.1, user data was in a SQLite Dict at $GRAMEXDATA/auth.user.db with BLOB value.
    From 1.87.0, it is stored in a gramex.data.filter compatible table with TEXT value.
    This function migrates the old database to the new format.
    '''
    import gramex
    import gramex.cache
    import sqlite3
    from gramex.config import objectpath, app_log, variables
    from urllib.parse import urlparse

    # No need to migrate if developer specifies a storelocation.user different from default.
    url = objectpath(gramex.service, 'storelocations.user.url', '')

    path = urlparse(url).path
    if os.path.sep != '/':
        path = path.lstrip('/').replace(os.path.sep, '/')
    default_path = variables['GRAMEXDATA'].replace(os.path.sep, '/').rstrip('/') + '/auth.user.db'
    if path != default_path:
        app_log.debug(f'1.87.0: SKIP migrating custom storelocations.user.url: {path}')
        return

    # No need to migrate unless user.value is a BLOB
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    query = "SELECT type FROM pragma_table_info('user') WHERE name='value'"
    if cur.execute(query).fetchall()[0][0].lower() == 'text':
        app_log.debug(f'1.87.0: SKIP migrated storelocations.user.url: {path}')
        return

    # SQLite can't change column type in a single command. So create new column, copy data, drop
    app_log.info(f'1.87.0: MIGRATING user.value from BLOB to TEXT: {path}')
    cur.executescript(
        '''
          ALTER TABLE user ADD COLUMN value2 TEXT;
          UPDATE user SET value2 = value;
          ALTER TABLE user DROP COLUMN value;
          ALTER TABLE user RENAME COLUMN value2 TO value;
        '''
    )

    conn.commit()
    conn.close()
