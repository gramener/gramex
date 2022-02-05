import re
import sys
import os.path
import sqlite3
from glob import glob
# lxml.etree is safe on https://github.com/tiran/defusedxml/tree/main/xmltestdata
from lxml.etree import Element              # nosec: lxml is fixed
from lxml.html import fromstring, tostring  # nosec: lxml is fixed
import numpy as np
import pandas as pd
import gramex.data
import gramex.cache
from gramex import conf
from gramex.config import app_log
from gramex.transforms import build_transform

if sys.version_info.major == 3:
    unicode = str

DB_CONFIG = {
    'table': 'agg{}',
    'levels': ['M', 'W', 'D'],
    'dimensions': [{'key': 'time', 'freq': '?level'},
                   'user.id', 'ip', 'status', 'uri'],
    'metrics': {
        'duration': ['count', 'sum'],
        'new_session': ['sum'],
        'session_time': ['sum']
    }
}

extra_columns = []
for key in conf.get('schedule', []):
    if 'kwargs' in conf.schedule[key] and 'custom_dims' in conf.schedule[key].kwargs:
        extra_columns = [dimension for dimension in conf.schedule[key].kwargs.custom_dims]

DB_CONFIG['dimensions'].extend(extra_columns)

DB_CONFIG['table_columns'] = [
    f'{k}_{x}'
    for k, v in DB_CONFIG['metrics'].items()
    for x in v] + [
        x['key'] if isinstance(x, dict) else x
        for x in DB_CONFIG['dimensions']]


FOLDER = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(FOLDER, 'config.yaml')


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
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
    return not pd.read_sql(query, conn, params=[table]).empty


def add_session(df, duration=30, cutoff_buffer=0):
    '''add new_session based on `duration` threshold
       add cutoff_buffer in minutes for first and last session requests
    '''
    s = df.groupby('user.id')['time'].diff().dt.total_seconds()
    flag = s.isnull() | s.ge(duration * 60)
    df['new_session'] = flag.astype(int)
    df['session_time'] = np.where(flag, cutoff_buffer * 60, s)
    return df


def prepare_logs(df, session_threshold=15, cutoff_buffer=0, custom_dims={}):
    '''
    - removes rows with errors in time, duration, status
    - sort by time
    - adds session metrics (new_session, session_time)
    '''
    df['time'] = pd.to_datetime(df['time'], unit='ms', errors='coerce')
    # Ignore pre-2000 year and null/NaT rows
    df = df[df['time'] > '2000-01-01']
    for col in ['duration', 'status']:
        if not np.issubdtype(df[col].dtype, np.number):
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df[df[col].notnull()]
    # logging via threads may not maintain order
    df = df.sort_values(by='time')

    for key, value in custom_dims.items():
        fn = build_transform({'function': value}, vars={'df': None}, iter=False)
        df[key] = fn(df)

    # add new_session
    df = add_session(df, duration=session_threshold, cutoff_buffer=cutoff_buffer)
    return df


def create_column_if_not_exists(table, freq, conn):
    for col in extra_columns:
        for row in conn.execute(f'PRAGMA table_info({table(freq)})'):
            if row[1] == col:
                break
        else:
            query = f'ALTER TABLE {table(freq)} ADD COLUMN "{col}" TEXT DEFAULT ""'
            conn.execute(query)
            conn.commit()


def summarize(transforms=[], post_transforms=[], run=True,
              session_threshold=15, cutoff_buffer=0, custom_dims=None):
    '''summarize'''
    app_log.info('logviewer: Summarize started')
    levels = DB_CONFIG['levels']
    table = DB_CONFIG['table'].format
    # dimensions and metrics to summarize
    groups = DB_CONFIG['dimensions']
    aggfuncs = DB_CONFIG['metrics']
    log_file = conf.log.handlers.requests.filename
    # Handle for multiple instances requests.csv$LISTENPORT
    log_file = '{0}{1}'.format(*log_file.partition('.csv'))
    folder = os.path.dirname(log_file)
    conn = sqlite3.connect(os.path.join(folder, 'logviewer.db'))

    for freq in levels:
        try:
            create_column_if_not_exists(table, freq, conn)
        except sqlite3.OperationalError:
            # Inform when table is created for the first time
            app_log.info('logviewer: OperationalError: Table does not exist')

    # drop agg tables from database
    if run in ['drop', 'reload']:
        droptable = 'DROP TABLE IF EXISTS {}'.format
        for freq in levels:
            app_log.info('logviewer: Dropping {} table'.format(table(freq)))
            conn.execute(droptable(table(freq)))
        conn.commit()
        conn.execute('VACUUM')
        if run == 'drop':
            conn.close()
            return
    # all log files sorted by modified time
    log_files = sorted(glob(log_file + '*'), key=os.path.getmtime)
    max_date = None

    def filesince(filename, date):
        match = re.search(r'(\d{4}-\d{2}-\d{2})$', filename)
        backupdate = match.group() if match else ''
        return backupdate >= date or backupdate == ''

    # get this month log files if db is already created
    if table_exists(table(levels[-1]), conn):
        query = 'SELECT MAX(time) FROM {}'.format(table(levels[-1]))    # nosec: table() is safe
        max_date = pd.read_sql(query, conn).iloc[0, 0]
        app_log.info(f'logviewer: last processed till {max_date}')
        this_month = max_date[:8] + '01'
        log_files = [f for f in log_files if filesince(f, this_month)]
        max_date = pd.to_datetime(max_date)

    if not log_files:
        app_log.info('logviewer: no log files to process')
        return
    # Create dataframe from log files
    columns = conf.log.handlers.requests['keys']
    # TODO: avoid concat?
    app_log.info(f'logviewer: files to process {log_files}')
    data = pd.concat([
        pd.read_csv(f, names=columns, encoding='utf-8').fillna('-')
        for f in log_files
    ], ignore_index=True)
    app_log.info(
        'logviewer: prepare_logs {} rows with {} mint session_threshold'.format(
            len(data.index), session_threshold))
    data = prepare_logs(df=data,
                        session_threshold=session_threshold,
                        cutoff_buffer=cutoff_buffer,
                        custom_dims=custom_dims)
    app_log.info('logviewer: processed and returned {} rows'.format(len(data.index)))
    # apply transforms on raw data
    app_log.info('logviewer: applying transforms')
    for spec in transforms:
        apply_transform(data, spec)  # applies on copy
    # levels should go from M > W > D
    for freq in levels:
        # filter dataframe for max_date.level
        if max_date:
            date_from = max_date
            if freq == 'W':
                date_from -= pd.offsets.Day(max_date.weekday())
            if freq == 'M':
                date_from -= pd.offsets.MonthBegin(1)
            data = data[data.time.ge(date_from)]
            # delete old records
            query = f'DELETE FROM {table(freq)} WHERE time >= ?'    # nosec: table() is safe
            conn.execute(query, (f'{date_from}',))
            conn.commit()
        groups[0]['freq'] = freq
        # get summary view
        app_log.info('logviewer: pdagg for {}'.format(table(freq)))
        dff = pdagg(data, groups, aggfuncs)
        # apply post_transforms here
        app_log.info('logviewer: applying post_transforms')
        for spec in post_transforms:
            apply_transform(dff, spec)
        # insert new records
        try:
            dff.to_sql(table(freq), conn, if_exists='append', index=False)
        # dff columns should match with table columns
        # if not, call summarize run='reload' to
        # drop all the tables and rerun the job
        except sqlite3.OperationalError:
            app_log.info('logviewer: OperationalError: run: reload')
            summarize(transforms=transforms, run='reload')
            return
    conn.close()
    app_log.info('logviewer: Summarize completed')
    return


def prepare_where(query, args, columns):
    '''prepare where clause'''
    wheres = []
    for key, vals in args.items():
        col, agg, op = gramex.data._filter_col(key, columns)
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
    if not wheres:
        return wheres
    prepend = 'WHERE ' if ' WHERE ' not in query else 'AND '
    wheres = prepend + wheres
    return wheres


def query(handler, args):
    '''queries for logviewer'''
    queries = handler.kwargs.kwargs.queries
    table = handler.path_kwargs.get('table')
    case = handler.path_kwargs.get('query')
    query = queries.get(case)
    wheres = prepare_where(query, args, DB_CONFIG['table_columns'])
    stmt = query.format(table=table, where=wheres)
    return stmt


def apply_transform(data, spec):
    '''apply transform on dataframe'''
    pandas_transforms = {
        'REPLACE': pd.Series.replace,
        'MAP': pd.Series.map,
        'IN': pd.Series.isin,
        'NOTIN': lambda s, v: ~s.isin(v),
        'CONTAINS': {
            'function': lambda s, v, **ops: s.str.contains(v, **ops),
            'defaults': {'case': False}
        },
        'NOTCONTAINS': {
            'function': lambda s, v, **ops: ~s.str.contains(v, **ops),
            'defaults': {'case': False}
        },
        'LEN': lambda s, _: s.str.len(),
        'LOWER': lambda s, _: s.str.lower(),
        'UPPER': lambda s, _: s.str.upper(),
        'PROPER': lambda s, _: s.str.capitalize(),
        'STARTSWITH': lambda s, v: s.str.startswith(v),
        'ENDSWITH': lambda s, v: s.str.endswith(v)
    }
    # TODO: STRREPLACE
    if spec['type'] == 'function':
        fn = build_transform(
            {'function': spec['expr']}, vars={'data': None},
            filename=f'lv: {spec.get("name")}')
        fn(data)  # applies on copy
        return data
    expr = spec['expr']
    func = pandas_transforms[expr['op']]
    kwargs = expr.get('kwargs', {})
    if isinstance(func, dict):
        # use defaults' kwargs if not present in expr.get
        for key, val in func.get('defaults', {}).items():
            if key not in kwargs:
                kwargs[key] = val
        func = func['function']
    data[spec['as']] = func(data[expr['col']], expr.get('value'), **kwargs)
    return data


def get_config(handler=None):
    '''return config as dict'''
    file_path = handler.kwargs.get('path_ui', CONFIG_FILE)
    return gramex.cache.open(file_path, 'config')


def load_component(page, **kwargs):
    '''return generateed template'''
    return gramex.cache.open(page, 'template', rel=True).generate(**kwargs)


def load_layout(config):
    '''return generated layout'''
    return tostring(eltree(config, root=Element('root')))[6:-7]


def eltree(data, root=None):
    '''Convert dict to etree.Element(s)'''
    attr_prefix = '@'
    text_key = '$'
    tpl_key = '_$'
    result = [] if root is None else root
    if isinstance(data, dict):
        for key, value in data.items():
            if root is not None:
                # attribute prefixes
                if key.startswith(attr_prefix):
                    key = key.lstrip(attr_prefix)
                    result.set(key, unicode(value))
                    continue
                # text content
                if key == text_key:
                    result.text = unicode(value)
                    continue
                # template hooks
                if key == tpl_key:
                    for tpl in value if isinstance(value, list) else [value]:
                        template = '{}.html'.format(tpl['tpl'])
                        raw_node = load_component(template, values=tpl.get('values', tpl))
                        result.append(fromstring(raw_node))
                    continue
            # add other keys as children
            values = value if isinstance(value, list) else [value]
            for value in values:
                elem = Element(key)
                result.append(elem)
                # scalars to text
                if not isinstance(value, (dict, list)):
                    value = {text_key: value}
                eltree(value, root=elem)
    else:
        result.append(Element(unicode(data)))
    return result
