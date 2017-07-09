'''Caching utilities'''
import io
import os
import six
import json
import yaml
import pandas as pd
from tornado.template import Template
from gramex.config import app_log


_opener_defaults = dict(mode='r', buffering=-1, encoding='utf-8', errors='strict',
                        newline=None, closefd=True)
_markdown_defaults = dict(output_format='html5', extensions=[
    'markdown.extensions.codehilite',
    'markdown.extensions.extra',
    'markdown.extensions.headerid',
    'markdown.extensions.meta',
    'markdown.extensions.sane_lists',
    'markdown.extensions.smarty',
])


def opener(callback, read=False):
    '''
    Converts any function that accepts a string or handle as its parameter into
    a function that takes the first parameter from a file path.

    For example, ``jsonload = opener(json.load)`` allows ``jsonload('x.json')``
    to return the parsed JSON contents of ``x.json``.

    For example, ``template = opener(string.Template, read=True)`` allows
    ```template('abc.txt').substitute(x=val)`` to load ``abc.txt``, convert it
    into a String template, and substitute values.

    Keyword arguments applicable for ``io.open`` are passed to ``io.open``. These
    default to ``io.open(mode='r', buffering=-1, encoding='utf-8',
    errors='strict', newline=None, closefd=True)``. All other arguments and
    keyword arguments are passed to the callback (e.g. to ``json.load``).

    When reading binary files, pass ``mode='rb', encoding=None, errors=None``.
    '''
    if not callable(callback):
        raise ValueError('opener requires a function as first parameter, not %s', repr(callback))
    if read:
        # Pass contents to callback
        def method(path, **kwargs):
            open_args = {key: kwargs.pop(key, val) for key, val in _opener_defaults.items()}
            with io.open(path, **open_args) as handle:
                return callback(handle.read(), **kwargs)
    else:
        # Pass handle to callback
        def method(path, **kwargs):
            open_args = {key: kwargs.pop(key, val) for key, val in _opener_defaults.items()}
            with io.open(path, **open_args) as handle:
                return callback(handle, **kwargs)
    return method


@opener
def _markdown(handle, **kwargs):
    from markdown import markdown
    return markdown(handle.read(), **{k: kwargs.pop(k, v) for k, v in _markdown_defaults.items()})


def stat(path):
    '''
    Returns a file status tuple - based on file last modified time and file size
    '''
    if os.path.exists(path):
        stat = os.stat(path)
        return (stat.st_mtime, stat.st_size)
    return (None, None)


# gramex.cache.open() stores its cache here.
# {(path, callback): {data: ..., stat: ...}}
_OPEN_CACHE = {}
# List of callback string methods
_CALLBACKS = dict(
    txt=opener(six.text_type, read=True),
    text=opener(six.text_type, read=True),
    yaml=opener(yaml.load),
    json=opener(json.load),
    csv=pd.read_csv,
    excel=pd.read_excel,
    xls=pd.read_excel,
    xlsx=pd.read_excel,
    hdf=pd.read_hdf,
    html=pd.read_html,
    sas=pd.read_sas,
    stata=pd.read_stata,
    table=pd.read_table,
    template=opener(Template, read=True),
    md=_markdown,
    markdown=_markdown,
)


def open(path, callback, **kwargs):
    '''
    Reads a file, processes it via a callback, caches the result and returns it.
    When called again, returns the cached result unless the file has updated.

    The callback can be a function that accepts the filename and any other
    arguments, or a string that can be one of

    - ``text`` or ``txt``: reads files using io.open
    - ``yaml``: reads files using PyYAML
    - ``json``: reads files using json.load
    - ``template``: reads files using tornado.Template
    - ``markdown`` or ``md``: reads files using markdown.markdown
    - ``csv``, ``excel``, ``xls``, `xlsx``, ``hdf``, ``html``, ``sas``,
      ``stata``, ``table``: reads using Pandas

    For example::

        # Load data.yaml as YAML into an AttrDict
        open('data.yaml', 'yaml')

        # Load data.json as JSON into an AttrDict
        open('data.json', 'json', object_pairs_hook=AttrDict)

        # Load data.csv as CSV into a Pandas DataFrame
        open('data.csv', 'csv', encoding='cp1252')

        # Load data using a custom callback
        open('data.fmt', my_format_reader_function, arg='value')
    '''
    # Pass _reload_status = True for testing purposes. This returns a tuple:
    # (result, reloaded) instead of just the result.
    _reload_status = kwargs.pop('_reload_status', False)
    reloaded = False
    _cache = kwargs.pop('_cache', _OPEN_CACHE)

    callback_is_str = isinstance(callback, six.string_types)
    key = (path, callback if callback_is_str else id(callback))
    cached = _cache.get(key, None)
    fstat = stat(path)
    if cached is None or fstat != cached.get('stat'):
        reloaded = True
        if callable(callback):
            data = callback(path, **kwargs)
        elif callback_is_str:
            method = _CALLBACKS.get(callback)
            if method is not None:
                data = method(path, **kwargs)
            else:
                raise TypeError('gramex.cache.open(callback="%s") is not a known type', callback)
        else:
            raise TypeError('gramex.cache.open(callback=) must be a function, not %r', callback)
        _cache[key] = {'data': data, 'stat': fstat}

    result = _cache[key]['data']
    return (result, reloaded) if _reload_status else result


# gramex.cache.query() stores its cache here
_QUERY_CACHE = {}
_STATUS_METHODS = {}


def _wheres(dbkey, tablekey, default_db, names, fn=None):
    '''
    Convert a table name list like ['sales', 'dept.sales']) to a WHERE clause
    like ``(table="sales") OR (db="dept" AND table="sales")``.

    TODO: escape the table names to avoid SQL injection attacks
    '''
    where = []
    for name in names:
        db, table = name.rsplit('.', 2) if '.' in name else (default_db, name)
        if not fn:
            where.append("({}='{}' AND {}='{}')".format(dbkey, db, tablekey, table))
        else:
            where.append("({}={}('{}') AND {}={}('{}'))".format(
                dbkey, fn[0], db, tablekey, fn[1], table))
    return ' OR '.join(where)


def _table_status(engine, tables):
    '''
    Returns the last updated date of a list of tables.
    '''
    # Cache the SQL query or file date check function beforehand.
    # Every time method is called with a URL and table list, run cached query
    dialect = engine.dialect.name
    key = (engine.url, tuple(tables))
    db = engine.url.database
    if _STATUS_METHODS.get(key, None) is None:
        if len(tables) == 0:
            raise ValueError('gramex.cache.query table list is empty: %s', repr(tables))
        for name in tables:
            if not name or not isinstance(name, six.string_types):
                raise ValueError('gramex.cache.query invalid table list: %s', repr(tables))
        if dialect == 'mysql':
            # https://dev.mysql.com/doc/refman/5.7/en/tables-table.html
            # Works only on MySQL 5.7 and above
            q = ('SELECT update_time FROM information_schema.tables WHERE ' +
                 _wheres('table_schema', 'table_name', db, tables))
        elif dialect == 'mssql':
            # https://goo.gl/b4aL9m
            q = ('SELECT last_user_update FROM sys.dm_db_index_usage_stats WHERE ' +
                 _wheres('database_id', 'object_id', db, tables, fn=['DB_ID', 'OBJECT_ID']))
        elif dialect == 'postgresql':
            # https://www.postgresql.org/docs/9.6/static/monitoring-stats.html
            q = ('SELECT n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_all_tables WHERE ' +
                 _wheres('schemaname', 'relname', 'public', tables))
        elif dialect == 'sqlite':
            if not db:
                raise KeyError('gramex.cache.query does not support memory sqlite "%s"' % dialect)
            q = db
        else:
            raise KeyError('gramex.cache.query cannot cache dialect "%s" yet' % dialect)
        if dialect == 'sqlite':
            _STATUS_METHODS[key] = lambda: stat(q)
        else:
            _STATUS_METHODS[key] = lambda: pd.read_sql(q, engine).to_json(orient='records')
    return _STATUS_METHODS[key]()


def query(sql, engine, state, **kwargs):
    '''
    Read SQL query or database table into a DataFrame. Caches results unless
    state has changed.

    The state can be specified in 3 ways:

    1. A string. This must be as a lightweight SQL query. If the result changes,
       the original SQL query is re-run.
    2. A function. This is called to determine the state of the database.
    3. A list of tables. This list of ["db.table"] names specifies which tables
       to watch for. This is currently experimental.
    '''
    # Pass _reload_status = True for testing purposes. This returns a tuple:
    # (result, reloaded) instead of just the result.
    _reload_status = kwargs.pop('_reload_status', False)
    reloaded = False
    _cache = kwargs.pop('_cache', _QUERY_CACHE)

    key = (sql, engine.url)
    current_status = _cache.get(key, {}).get('status', None)
    if isinstance(state, (list, tuple)):
        status = _table_status(engine, tuple(state))
    elif isinstance(state, six.string_types):
        status = pd.read_sql(state, engine).to_dict(orient='list')
    elif callable(state):
        status = state()
    else:
        raise TypeError('gramex.cache.query(state=) must be a table list, query or fn, not %s',
                        repr(state))

    if status != current_status:
        _cache[key] = {
            'data': pd.read_sql(sql, engine, **kwargs),
            'status': status,
        }
        reloaded = True

    result = _cache[key]['data']
    return (result, reloaded) if _reload_status else result


# gramex.cache.reload_module() stores its cache here. {module_name: file_stat}
_MODULE_CACHE = {}


def reload_module(*modules):
    '''
    Reloads one or more modules if they are outdated, i.e. only if required the
    underlying source file has changed.

    For example::

        import mymodule             # Load cached module
        reload_module(mymodule)     # Reload module if the source has changed

    This is most useful during template development. If your changes are in a
    Python module, add adding these lines to pick up new module changes when
    the template is re-run.
    '''
    for module in modules:
        name = getattr(module, '__name__', None)
        path = getattr(module, '__file__', None)
        if name is None or path is None or not os.path.exists(path):
            app_log.warn('Path for module %s is %s: not found', name, path)
            continue
        # On Python 3, __file__ points to the .py file. In Python 2, it's the .pyc file
        # https://www.python.org/dev/peps/pep-3147/#file
        if path.lower().endswith('.pyc'):
            path = path[:-1]
            if not os.path.exists(path):
                app_log.warn('Path for module %s is %s: not found', name, path)
                continue
        # The first time, don't reload it. Thereafter, if it's older or resized, reload it
        fstat = stat(path)
        if fstat != _MODULE_CACHE.get(name, fstat):
            app_log.info('Reloading module %s', name)
            six.moves.reload_module(module)
        _MODULE_CACHE[name] = fstat
