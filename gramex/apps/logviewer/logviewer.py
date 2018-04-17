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
import sys
import os.path
import sqlite3
from glob import glob
from lxml.etree import Element
from lxml.html import fromstring, tostring
import numpy as np
import pandas as pd
import gramex.data
import gramex.cache
from gramex import conf

if sys.version_info.major == 3:
    unicode = str

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


def prepare_logs(df):
    '''prepare gramex logs'''
    df['time'] = pd.to_datetime(df['time'], unit='ms', errors='coerce')
    df = df[df['time'].notnull()]
    for col in ['duration', 'status']:
        if not np.issubdtype(df[col].dtype, np.number):
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df[df[col].notnull()]
    # logging via threads may not maintain order
    df = df.sort_values(by='time')
    # add new_session
    df = add_session(df, duration=15)
    return df


def summarize(transforms=[], run=True):
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
    if run in ['drop', 'reload']:
        droptable = 'DROP TABLE IF EXISTS {}'.format
        for freq in levels:
            conn.execute(droptable(table(freq)))
        conn.commit()
        conn.execute('VACUUM')
        if run == 'drop':
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
    data = prepare_logs(data)
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
        # TODO: apply transforms here
        for spec in transforms:
            apply_transform(dff, spec)
        # insert new records
        try:
            dff.to_sql(table(freq), conn, if_exists='append', index=False)
        # dff columns should match with table columns
        # if not, call summarize run='reload' to
        # drop all the tables and rerun the job
        except sqlite3.OperationalError:
            summarize(transforms=transforms, run='reload')
            return
    conn.close()
    return


def prepare_where(query, args, columns):
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
        }
    }
    expr = spec['expr']
    func = pandas_transforms[expr['op']]
    kwargs = expr.get('kwargs', {})
    if isinstance(func, dict):
        # collect default kwargs if not present
        for key, val in func.get('defaults', {}).items():
            if key not in kwargs:
                kwargs[key] = val
        func = func['function']
    data[spec['as']] = func(data[expr['col']], expr['value'], **kwargs)
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
