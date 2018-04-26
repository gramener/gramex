'''Caching utilities'''
from __future__ import unicode_literals

import io
import os
import six
import sys
import json
import time
import atexit
import inspect
import requests
import tempfile
import mimetypes
import subprocess       # nosec
import pandas as pd
from threading import Thread
from tornado.concurrent import Future
from gramex.config import app_log, merge
from six.moves.urllib_parse import urlparse


MILLISECOND = 0.001         # in seconds
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
# A set of temporary files to delete on program exit
_TEMP_FILES = set()


def _delete_temp_files():
    for path in _TEMP_FILES:
        if os.path.exists(path):
            os.remove(path)


atexit.register(_delete_temp_files)


def cache_key(*args):
    '''Converts arguments into a string suitable for use as a cache key'''
    return json.dumps(args, sort_keys=True, separators=(',', ':'))


def opener(callback, read=False, **open_kwargs):
    '''
    Converts any function that accepts a string or handle as its parameter into
    a function that takes the first parameter from a file path.

    Here are a few examples::

        jsonload = opener(json.load)
        jsonload('x.json')      # opens x.json and runs json.load(handle)
        gramex.cache.open('x.json', jsonload)   # Loads x.json, cached

        # read=True parameter passes the contents (not handle) to the function
        template = opener(string.Template, read=True)
        template('abc.txt').substitute(x=val)
        gramex.cache.open('abc.txt', template).substitute(x=val)

        # If read=True, callback may be None. The result of .read() is passed as-is
        text = opener(None, read=True)
        gramex.cache.open('abc.txt', text)

    Keyword arguments applicable for ``io.open`` are passed to ``io.open``. These
    default to ``io.open(mode='r', buffering=-1, encoding='utf-8',
    errors='strict', newline=None, closefd=True)``. All other arguments and
    keyword arguments are passed to the callback (e.g. to ``json.load``).

    When reading binary files, pass ``mode='rb', encoding=None, errors=None``.
    '''
    merge(open_kwargs, _opener_defaults, 'setdefault')
    if read:
        # Pass contents to callback
        def method(path, **kwargs):
            open_args = {key: kwargs.pop(key, val) for key, val in open_kwargs.items()}
            with io.open(path, **open_args) as handle:
                result = handle.read()
                return callback(result, **kwargs) if callable(callback) else result
    else:
        if not callable(callback):
            raise ValueError('opener callback %s not a function', repr(callback))

        # Pass handle to callback
        def method(path, **kwargs):
            open_args = {key: kwargs.pop(key, val) for key, val in open_kwargs.items()}
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


def hashed(val):
    '''Return the hashed value of val. If not possible, return None'''
    try:
        hash(val)
        return val
    except TypeError:
        try:
            return json.dumps(val, sort_keys=True, separators=(',', ':'))
        except Exception:
            return None


# gramex.cache.open() stores its cache here.
# {(path, callback): {data: ..., stat: ...}}
_OPEN_CACHE = {}
_OPEN_CALLBACKS = dict(
    bin=opener(None, read=True, mode='rb', encoding=None, errors=None),
    txt=opener(None, read=True),
    text=opener(None, read=True),
    csv=pd.read_csv,
    excel=pd.read_excel,
    xls=pd.read_excel,
    xlsx=pd.read_excel,
    hdf=pd.read_hdf,
    html=pd.read_html,
    sas=pd.read_sas,
    stata=pd.read_stata,
    table=pd.read_table,
    md=_markdown,
    markdown=_markdown,
)


def open(path, callback=None, transform=None, rel=False, **kwargs):
    '''
    Reads a file, processes it via a callback, caches the result and returns it.
    When called again, returns the cached result unless the file has updated.

    By default, it determine the file type using the extension. For example::

        open('data.yaml')           # Loads a YAML file
        open('data.csv')            # Loads a CSV file

    The 2nd parameter (callback) a predefined string that can be one of

    - ``bin``: reads binary files using io.open
    - ``text`` or ``txt``: reads text files using io.open
    - ``yaml``: reads files using yaml.load via io.open
    - ``config``: reads files using using :py:class:`gramex.config.PathConfig`.
      Same as ``yaml``, but allows ``import:`` and variable substitution.
    - ``json``: reads files using json.load via io.open
    - ``template``: reads files using tornado.Template via io.open
    - ``markdown`` or ``md``: reads files using markdown.markdown via io.open
    - ``csv``, ``excel``, ``xls``, `xlsx``, ``hdf``, ``html``, ``sas``,
      ``stata``, ``table``: reads using Pandas
    - ``xml``, ``svg``, ``rss``, ``atom``: reads using lxml.etree

    For example::

        # Load data.yaml as YAML into an AttrDict
        open('data.yaml', 'yaml')

        # Load data.json as JSON into an AttrDict
        open('data.json', 'json', object_pairs_hook=AttrDict)

        # Load data.csv as CSV into a Pandas DataFrame
        open('data.csv', 'csv', encoding='cp1252')

    It can also be a function that accepts the filename and any other arguments::

        # Load data using a custom callback
        open('data.fmt', my_format_reader_function, arg='value')

    This is called as ``my_format_reader_function('data.fmt', arg='value')`` and
    cached. Future calls do not re-load and re-calculate this data.

    ``transform=`` is an optioanl function that processes the data returned by
    the callback. For example::

        # Returns the count of the CSV file, updating it only when changed
        open('data.csv', 'csv', transform=lambda data: len(data))

        # After loading data.xlsx into a DataFrame, returned the grouped result
        open('data.xlsx', 'xslx', transform=lambda data: data.groupby('city')['sales'].sum())

    If ``transform=`` is not a callable, it is ignored.

    ``rel=True`` opens the path relative to the caller function's file path. If
    ``D:/app/calc.py`` calls ``open('data.csv', 'csv', rel=True)``, the path
    is replaced with ``D:/app/data.csv``.

    Any other keyword arguments are passed directly to the callback. If the
    callback is a predefined string and uses io.open, all argument applicable to
    io.open are passed to io.open and the rest are passed to the callback.
    '''
    # Pass _reload_status = True for testing purposes. This returns a tuple:
    # (result, reloaded) instead of just the result.
    _reload_status = kwargs.pop('_reload_status', False)
    reloaded = False
    _cache = kwargs.pop('_cache', _OPEN_CACHE)

    # Get the parent frame's filename. Compute path relative to that.
    if rel:
        stack = inspect.getouterframes(inspect.currentframe(), 2)
        folder = os.path.dirname(os.path.abspath(stack[1][1]))
        path = os.path.join(folder, path)

    original_callback = callback
    if callback is None:
        callback = os.path.splitext(path)[-1][1:]
    callback_is_str = isinstance(callback, six.string_types)
    key = (
        path,
        original_callback if callback_is_str else id(callback),
        id(transform),
        frozenset(((k, hashed(v)) for k, v in kwargs.items())),
    )
    cached = _cache.get(key, None)
    fstat = stat(path)
    if cached is None or fstat != cached.get('stat'):
        reloaded = True
        if callable(callback):
            data = callback(path, **kwargs)
        elif callback_is_str:
            method = None
            if callback in _OPEN_CALLBACKS:
                method = _OPEN_CALLBACKS[callback]
            elif callback in {'yml', 'yaml'}:
                import yaml
                method = opener(yaml.load)
            elif callback in {'json'}:
                import json
                method = opener(json.load)
            elif callback in {'template', 'tmpl'}:
                from tornado.template import Template
                method = opener(Template, read=True)
            elif callback in {'config'}:
                from gramex.config import PathConfig
                method = PathConfig
            elif callback in {'xml', 'svg', 'rss', 'atom'}:
                from lxml import etree
                method = etree.parse

            if method is not None:
                data = method(path, **kwargs)
            elif original_callback is None:
                raise TypeError('gramex.cache.open: path "%s" has unknown extension' % path)
            else:
                raise TypeError('gramex.cache.open(callback="%s") is not a known type' % callback)
        else:
            raise TypeError('gramex.cache.open(callback=) must be a function, not %r' % callback)
        if callable(transform):
            data = transform(data)
        _cache[key] = {'data': data, 'stat': fstat}

    result = _cache[key]['data']
    return (result, reloaded) if _reload_status else result


_SAVE_CALLBACKS = dict(
    json='to_json',
    csv='to_csv',
    xlsx='to_excel',
    hdf='to_hdf',
    html='to_html',
    stata='to_stata',
    # Other configurations not supported
)


def save(data, url, callback=None, **kwargs):
    '''
    Saves a DataFrame into file at url. It does not cache.

    ``callback`` is almost the same as for :py:func:`gramex.cache.open`. It can
    be ``json``, ``csv``, ``xlsx``, ``hdf``, ``html``, ``stata`` or
    a function that accepts the filename and any other arguments.

    Other keyword arguments are passed directly to the callback.
    '''
    if callback is None:
        callback = os.path.splitext(url)[-1][1:]
    if callable(callback):
        return callback(data, url, **kwargs)
    elif callback in _SAVE_CALLBACKS:
        method = getattr(data, _SAVE_CALLBACKS[callback])
        argspec = inspect.getargspec(method)
        # Remove arguments
        if argspec.keywords is None:
            kwargs = {key: val for key, val in kwargs.items() if key in argspec.args}
        return method(url, **kwargs)
    else:
        raise TypeError('gramex.cache.save(callback="%s") is unknown' % callback)


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


def query(sql, engine, state=None, **kwargs):
    '''
    Read SQL query or database table into a DataFrame. Caches results unless
    state has changed. It always re-runs the query unless state is specified.

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
    elif state is None:
        # Create a new status every time, so that the query is always re-run
        status = object()
    else:
        raise TypeError('gramex.cache.query(state=) must be a table list, query or fn, not %s',
                        repr(state))

    if status != current_status:
        _cache[key] = {
            'data': pd.read_sql(sql, engine, **kwargs),
            'status': status,
        }
        app_log.debug('gramex.cache.query: %s. engine: %s. state: %s. kwargs: %s', sql, engine,
                      state, kwargs)
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
            app_log.warning('Path for module %s is %s: not found', name, path)
            continue
        # On Python 3, __file__ points to the .py file. In Python 2, it's the .pyc file
        # https://www.python.org/dev/peps/pep-3147/#file
        if path.lower().endswith('.pyc'):
            path = path[:-1]
            if not os.path.exists(path):
                app_log.warning('Path for module %s is %s: not found', name, path)
                continue
        # The first time, don't reload it. Thereafter, if it's older or resized, reload it
        fstat = stat(path)
        if fstat != _MODULE_CACHE.get(name, fstat):
            app_log.info('Reloading module %s', name)
            six.moves.reload_module(module)
        _MODULE_CACHE[name] = fstat


def urlfetch(path, **kwargs):
    '''
    If path is a file path, return the path as-is.
    If path is a URL, download the file, return the saved filename.
    The filename extension is based on the URL's Content-Type HTTP header.
    Any other keyword arguments are passed to requests.get.
    Automatically delete the files on exit of the application.
    This is a synchronous function, i.e. it waits until the file is downloaded.
    '''
    url = urlparse(path)
    if url.scheme not in {'http', 'https'}:
        return path
    r = requests.get(path, **kwargs)
    if 'Content-Type' in r.headers:
        content_type = r.headers['Content-Type'].split(';')[0]
        ext = mimetypes.guess_extension(content_type, strict=False)
    else:
        ext = os.path.splitext(url.path)[1]
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as handle:
        for chunk in r.iter_content(chunk_size=16384):
            handle.write(chunk)
    _TEMP_FILES.add(handle.name)
    return handle.name


class Subprocess(object):
    '''
    tornado.process.Subprocess does not work on Windows.
    https://github.com/tornadoweb/tornado/issues/1585

    This is a threaded alternative based on
    http://stackoverflow.com/a/4896288/100904

    Usage::

        proc = Subprocess(
            args,
            stream_stdout=[self.write],     # List of write methods to stream stdout to
            stream_stderr=[self.write],     # List of write methods to stream stderr to
            buffer_size='line',             # Write line by line. Can also be a number of bytes
            **kwargs
        )
        stdout, stderr = yield proc.wait_for_exit()
        if proc.proc.returncode:
            raise Exception('Process failed with return code %d', proc.proc.returncode)

    :arg list args: command line arguments passed as a list to Subprocess
    :arg methodlist stream_stdout: optional list of write methods - called when stdout has data
    :arg methodlist stream_stderr: optional list of write methods - called when stderr has data
    :arg str_or_int buffer_size: 'line' to write line by line. number for chunk size
    :arg dict kwargs: additional kwargs passed to subprocess.Popen

    stream_stdout and stream_stderr can be a list of functions that accept a byte
    string and process it.

    If stream_stdout is empty or missing, the returned ``stdout`` value contains
    the stdout contents as bytes. Otherwise, it is passed to all stream_stdout
    methods and the returned ``stdout`` is empty. (Same for ``stderr``)

    Examples::

        stdout, stderr = yield Subprocess(['ls', '-la']).wait_for_exit()
        _, stderr = yield Subprocess(['git', 'log'], stream_stdout=[handler.write]).wait_for_exit()
    '''
    def __init__(self, args, stream_stdout=[], stream_stderr=[], buffer_size=0, **kwargs):
        self.args = args

        # self.proc.stdout & self.proc.stderr are streams with process output
        kwargs['stdout'] = kwargs['stderr'] = subprocess.PIPE

        # On UNIX, close all file descriptors except 0, 1, 2 before child
        # process is executed. I've no idea why. Copied from
        # http://stackoverflow.com/a/4896288/100904
        kwargs['close_fds'] = 'posix' in sys.builtin_module_names

        self.proc = subprocess.Popen(args, **kwargs)        # nosec
        self.thread = {}        # Has the running threads
        self.future = {}        # Stores the futures indicating stream close

        # Buffering has 2 modes. buffer_size='line' reads and writes line by line
        # buffer_size=<number> reads in byte chunks. Define the appropriate method
        if hasattr(buffer_size, 'lower') and 'line' in buffer_size.lower():
            def _write(stream, callbacks, future, retval):
                '''Call callbacks with content from stream. On EOF mark future as done'''
                while True:
                    content = stream.readline()
                    if len(content) > 0:
                        if isinstance(content, six.text_type):
                            content = content.encode('utf-8')
                        for callback in callbacks:
                            callback(content)
                    else:
                        stream.close()
                        break
                while self.proc.poll() is None:
                    time.sleep(MILLISECOND)
                future.set_result(retval())
        else:
            # If the buffer size is 0 or negative, use the default buffer size to read
            if buffer_size <= 0:
                buffer_size = io.DEFAULT_BUFFER_SIZE

            def _write(stream, callbacks, future, retval):
                '''Call callbacks with content from stream. On EOF mark future as done'''
                while True:
                    content = stream.read(buffer_size)
                    size = len(content)
                    if size > 0:
                        if isinstance(content, six.text_type):
                            content = content.encode('utf-8')
                        for callback in callbacks:
                            # This may raise a ValueError: write to closed file.
                            # TODO: decide how to handle it.
                            callback(content)
                    if size < buffer_size:
                        stream.close()
                        break
                while self.proc.poll() is None:
                    time.sleep(MILLISECOND)
                future.set_result(retval())

        callbacks_lookup = {'stdout': stream_stdout, 'stderr': stream_stderr}
        for stream in ('stdout', 'stderr'):
            callbacks = callbacks_lookup[stream]
            # If stream_stdout or stream_stderr are not defined, construct a
            # BytesIO and return its value when the stream is closed
            if not callbacks:
                ret_stream = io.BytesIO()
                callbacks = [ret_stream.write]
                retval = ret_stream.getvalue
            else:
                retval = lambda: b''        # noqa
            self.future[stream] = future = Future()
            # Thread writes from self.proc.stdout / stderr to appropriate callbacks
            self.thread[stream] = t = Thread(
                target=_write,
                args=(getattr(self.proc, stream), callbacks, future, retval))
            t.daemon = True     # Thread dies with the program
            t.start()

    def wait_for_exit(self):
        '''
        Returns futures for (stdout, stderr). To wait for the process to complete, use::

            stdout, stderr = yield proc.wait_for_exit()
        '''
        return [self.future['stdout'], self.future['stderr']]
