import io
import os
import six
import json
import logging
import sqlalchemy as sa
import pandas as pd
from glob import glob
from tornado.web import HTTPError
from gramex.http import BAD_REQUEST
import gramex
import gramex.data
from gramex.config import app_log, variables

folder = os.path.dirname(os.path.abspath(__file__))
template = os.path.join(folder, 'index.html')


def gramexupdate(handler):
    # When a user casually visits the page, render friendly output
    if handler.request.method == 'GET':
        return gramex.cache.open(template, 'template').generate(
            version=gramex.__version__, handler=handler)
    # Log all messages
    try:
        logs = json.loads(handler.request.body, encoding='utf-8')
        if not isinstance(logs, list):
            raise ValueError()
    except (ValueError, AssertionError):
        raise HTTPError(BAD_REQUEST, reason='Invalid POST data. Expecting JSON array')
    logger = logging.getLogger('gramexupdate')
    for log in logs:
        log['ip'] = handler.request.remote_ip
        logger.info(json.dumps(log, ensure_ascii=True, separators=(',', ':')))
    # Return the latest Gramex version
    return {'version': gramex.__version__}


def consolidate():
    '''Consolidate log data into a database'''
    log_file = variables['LOGFILE']
    data_file = variables['LOGDB']

    # Connect to DB and initialize
    data_url = 'sqlite:///' + data_file
    engine = sa.create_engine(data_url)
    engine.execute('''CREATE TABLE IF NOT EXISTS logs (
        src TEXT, time INT, event TEXT, ip TEXT,
        system TEXT, node TEXT, release TEXT, version TEXT, machine TEXT, processor TEXT,
        pid NUM, args TEXT, cwd TEXT, dir TEXT,
        date TEXT
    )''')

    merged = set(gramex.data.filter(url=data_url, query='SELECT DISTINCT src FROM logs')['src'])

    def merge(path, force=False):
        '''Merge log file from path into database'''
        src = os.path.split(path)[-1]
        if src in merged and not force:
            return
        app_log.info('consolidating %s', src)

        result = []
        for line in io.open(path, 'r', encoding='utf-8'):
            row = json.loads(line)
            row['src'] = src

            # uname is a list. Convert into system data
            (row['system'], row['node'], row['release'], row['version'],
             row['machine'], row['processor']) = row.pop('uname')

            row_data = row.pop('data')
            row_data = json.loads(row_data) if row_data else {}     # parse. Ignore missing data
            # If data is double-encoded, decode again. TODO: figure out when & why
            if isinstance(row_data, six.string_types):
                row_data = json.loads(row_data)
            # Startup args are a list. Join with spaces
            if 'args' in row_data and isinstance(row_data['args'], list):
                row_data['args'] = ' '.join(row_data['args'])
            row.update(row_data)

            result.append(row)
        # Post-process results
        result = pd.DataFrame(result)
        ns = 1E9        # nanosecond conversion
        result['date'] = pd.to_datetime(result['time'] * ns).dt.strftime('%Y-%m-%d')
        result['time'] = result['time'].astype(int)

        # Replace rows for file currently processed
        engine.execute('DELETE FROM logs WHERE src=?', src)
        # SQLite supports 999 variables in an insert by default.
        # chunksize=60 ensures that 15 columns x 60 = 750 is within the limit.
        result.to_sql('logs', engine, if_exists='append', index=False, chunksize=60)

    merge(log_file, force=True)
    for log_file in glob(log_file + '*'):
        merge(log_file, force=False)

    return 'Processed'
