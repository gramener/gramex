'''logviewer
requests.csv*
default keys - ['time', 'ip', 'user.id', 'status',
                'duration', 'method', 'uri', 'error']
mandatory keys - ['time', 'ip', 'user.id', 'status',
                'duration', 'uri']
custom metrics
    new_session
    new_login :todo
'''
import os.path
import sqlite3
from glob import glob
import numpy as np
import pandas as pd
import gramex.data
from gramex import conf

DB_CONFIG = {
    'table': 'agg{}',
    'levels': ['M', 'W', 'D'],
    'dimensions': [{'key': 'time', 'freq': '?level'},
                   'user.id', 'ip', 'status', 'uri'],
    'metrics': {
        'duration': ['count', 'sum', 'mean'],
        'new_session': ['sum'],
        'session_time': ['sum', 'mean']
    }
}
DB_CONFIG['table_columns'] = [
    '{}_{}'.format(k, x)
    for k, v in DB_CONFIG['metrics'].items()
    for x in v] + [
        x['key'] if isinstance(x, dict) else x
        for x in DB_CONFIG['dimensions']]


def pdagg(df, groups, aggfuncs):
    '''
    groups = [{'key': 'time', 'freq': 'D'}, 'user.id', 'status', 'uri']
    aggfuncs = {'duration': ['count', 'mean', namedfunc], 'status': ['count']}
    '''
    groups = [pd.Grouper(**g) if isinstance(g, dict) else g for g in groups]
    grps = df.groupby(groups)
    dff = grps.agg(aggfuncs)
    if isinstance(dff.columns, pd.MultiIndex):
        dff.columns = dff.columns.map('_'.join)
    return dff.reset_index()


def table_exists(table, conn):
    '''check if table exists in sqlite db'''
    query = ("SELECT name FROM sqlite_master "
             "WHERE type='table' AND name='{}'".format(table))
    return not pd.read_sql(query, conn).empty


def add_session(df, duration=30):
    '''add new_session'''
    s = df.groupby('user.id')['time'].diff().dt.total_seconds()
    flag = s.isnull() | s.ge(duration * 60)
    df['new_session'] = flag.astype(int)
    df['session_time'] = np.where(flag, 0, s)
    return df


def summarize(drop=False):
    '''summarize'''
    levels = DB_CONFIG['levels']
    table = DB_CONFIG['table'].format
    # dimensions and metrics to summarize
    groups = DB_CONFIG['dimensions']
    aggfuncs = DB_CONFIG['metrics']
    log_file = conf.log.handlers.requests.filename
    folder = os.path.dirname(log_file)
    conn = sqlite3.connect(os.path.join(folder, 'logviewer.db'))
    # drop agg tables from database
    if drop:
        droptable = 'DROP TABLE IF EXISTS {}'.format
        for freq in levels:
            conn.execute(droptable(table(freq)))
        conn.commit()
        conn.execute('VACUUM')
        conn.close()
        return
    # all log files sorted by modified time
    log_files = sorted(glob(log_file + '*'), key=os.path.getmtime)
    dt = None
    # get this month log files if db is already created
    if table_exists(table(levels[-1]), conn):
        dt = pd.read_sql(
            'SELECT MAX(time) FROM {}'.format(
                table(levels[-1])), conn).iloc[0, 0]
        log_limit = '{}.{}'.format(log_files[-1], dt[:8] + '01')
        log_files = [f for f in log_files if f > log_limit] + [log_files[-1]]
        dt = pd.to_datetime(dt)
    if not log_files:
        return
    # Create dataframe from log files
    columns = conf.log.handlers.requests['keys']
    # TODO: aviod concat?
    data = pd.concat([
        gramex.cache.open(f, 'csv', names=columns).fillna('-')
        for f in log_files
    ], ignore_index=True)
    data['time'] = pd.to_datetime(data['time'], unit='ms', errors='coerce')
    data = data[data['time'].notnull()]
    if not np.issubdtype(data['duration'].dtype, np.number):
        data['duration'] = pd.to_numeric(data['duration'], errors='coerce')
        data = data[data['duration'].notnull()]
    # logging via threads may not maintain order
    data = data.sort_values(by='time')
    # add new_session
    data = add_session(data, duration=15)
    delete = 'DELETE FROM {} WHERE time >= "{}"'.format
    # levels should go from M > W > D
    for freq in levels:
        # filter dataframe for dt.level
        if dt:
            dtt = dt
            if freq == 'W':
                dtt -= pd.offsets.Day(dt.weekday())
            if freq == 'M':
                dtt -= pd.offsets.MonthBegin(1)
            data = data[data.time.ge(dtt)]
            # delete old records
            conn.execute(delete(table(freq), dtt))
            conn.commit()
        groups[0]['freq'] = freq
        # get summary view
        dff = pdagg(data, groups, aggfuncs)
        # insert new records
        dff.to_sql(table(freq), conn, if_exists='append', index=False)
    conn.close()
    return


def prepare_where(args, columns):
    '''prepare where clause'''
    wheres = []
    for key, vals in args.items():
        col, op = gramex.data._filter_col(key, columns)
        if col not in columns:
            continue
        if op == '':
            wheres.append('"{}" IN ("{}")'.format(col, '", "'.join(vals)))
        elif op == '!':
            wheres.append('"{}" NOT IN ("{}")'.format(col, '", "'.join(vals)))
        elif op == '>':
            wheres.append('"{}" > "{}"'.format(col, min(vals)))
        elif op == '>~':
            wheres.append('"{}" >= "{}"'.format(col, min(vals)))
        elif op == '<':
            wheres.append('"{}" < "{}"'.format(col, max(vals)))
        elif op == '<~':
            wheres.append('"{}" <= "{}"'.format(col, max(vals)))
        elif op == '~':
            q = ' OR '.join('"{}" LIKE "%{}%"'.format(col, x) for x in vals)
            wheres.append('({})'.format(q))
        elif op == '!~':
            q = ' OR '.join('"{}" NOT LIKE "%{}%"'.format(col, x) for x in vals)
            wheres.append('({})'.format(q))
    wheres = ' AND '.join(wheres)
    wheres = 'WHERE ' + wheres if wheres else wheres
    return wheres


def query(handler, args):
    '''queries for logviewer'''
    queries = {
        'kpi-pageviews': (
            'SELECT SUM(duration_count) AS value FROM {table} {where}'
        ),
        'kpi-sessions': (
            'SELECT SUM(new_session_sum) AS value FROM {table} {where}'
        ),
        'kpi-users': (
            'SELECT COUNT(DISTINCT "user.id") AS value FROM {table} {where}'
        ),
        'kpi-avgtimespent': (
            'SELECT SUM(session_time_sum)/SUM(new_session_sum) AS value'
            ' FROM {table} {where}'
        ),
        'kpi-urls': (
            'SELECT COUNT(DISTINCT uri) AS value FROM {table} {where}'
        ),
        'kpi-avgloadtime': (
            'SELECT SUM(duration_sum)/SUM(duration_count) AS value'
            ' FROM {table} {where}'
        ),
        'toptenusers': (
            'SELECT "user.id", SUM(duration_count) AS views'
            ' FROM {table} {where} GROUP BY "user.id" ORDER BY views DESC LIMIT 10'
        ),
        'toptenip': (
            'SELECT ip, SUM(duration_count) AS views'
            ' FROM {table} {where} GROUP BY ip ORDER BY views DESC LIMIT 10'
        ),
        'toptenstatus': (
            'SELECT status, SUM(duration_count) AS views'
            ' FROM {table} {where} GROUP BY status ORDER BY views DESC LIMIT 10'
        ),
        'toptenuri': (
            'SELECT uri, SUM(duration_count) AS views'
            ' FROM {table} {where} GROUP BY uri ORDER BY views DESC LIMIT 10'
        ),
        'pageviewstrend': (
            'SELECT time, SUM(duration_count) AS pageviews'
            ' FROM {table} {where} GROUP BY time'
        ),
        'sessionstrend': (
            'SELECT time, SUM(new_session_sum) AS sessions'
            ' FROM {table} {where} GROUP BY time'
        ),
        'loadtimetrend': (
            'SELECT time, SUM(duration_sum)/SUM(duration_count) AS loadtime'
            ' FROM {table} {where} GROUP BY time'
        ),
        'loadtimeviewstrend': (
            'SELECT time, SUM(duration_sum)/SUM(duration_count) AS loadtime,'
            'SUM(duration_count) AS views'
            ' FROM {table} {where} GROUP BY time'
        )
    }
    table = handler.path_kwargs.get('table')
    case = handler.path_kwargs.get('query')
    wheres = prepare_where(args, DB_CONFIG['table_columns'])
    stmt = queries.get(case).format(table=table, where=wheres)
    return stmt
