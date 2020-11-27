'''
Interact with data from the browser
'''
import io
import os
import re
import six
import time
import json
import sqlalchemy as sa
import pandas as pd
import gramex.cache
from tornado.escape import json_encode
from gramex.config import merge, app_log
from orderedattrdict import AttrDict

_ENGINE_CACHE = {}
_METADATA_CACHE = {}
_FOLDER = os.path.dirname(os.path.abspath(__file__))
# Dummy path used by _path_safe to detect sub-directories
_path_safe_root = os.path.realpath('/root/dir')
# Aggregator separator. ?col|SUM treats SUM as an aggregate function
_agg_sep = '|'
# List of aggregated types returned by operators (if different from column type)
# Note: For aggregation functions, see:
# SQLite: https://www.sqlite.org/lang_aggfunc.html
# MySQL: https://dev.mysql.com/doc/refman/8.0/en/group-by-functions.html
# PostgreSQL: https://www.postgresql.org/docs/9.5/static/functions-aggregate.html
# SQL Server: http://bit.ly/2MYPgQi
# DB2: https://ibm.co/2Kfbnjw
# Oracle: https://docs.oracle.com/database/121/SQLRF/functions003.htm
_agg_type = {
    'sum': float,
    'count': int,
    'avg': float,
    'stdev': float,         # MS SQL version of stddev
    'stddev': float,
    'rank': int,
    'percent_rank': float,
    # The following types are the same as the columns
    # first, last, min, max, median
}
# List of Python types returned by SQLAlchemy
_numeric_types = {'int', 'long', 'float', 'Decimal'}


def _transform_fn(transform, transform_kwargs):
    if transform is not None and transform_kwargs is not None:
        return lambda v: transform(v, **transform_kwargs)
    return transform


def _replace(engine, args, *vars, **kwargs):
    escape = _sql_safe if engine == 'sqlalchemy' else _path_safe
    params = {k: v[0] for k, v in args.items() if len(v) > 0 and escape(v[0])}

    def _format(val):
        if isinstance(val, six.string_types):
            return val.format(**params)
        if isinstance(val, list):
            return [_format(v) for v in val]
        if isinstance(val, dict):
            return AttrDict([(k, _format(v)) for k, v in val.items()])
        return val

    return _format(list(vars)) + [_format(kwargs)]


def filter(url, args={}, meta={}, engine=None, ext=None, columns=None,
           query=None, queryfile=None, transform=None, transform_kwargs=None, **kwargs):
    '''
    Filters data using URL query parameters. Typical usage::

        filtered = gramex.data.filter(dataframe, args=handler.args)
        filtered = gramex.data.filter('file.csv', args=handler.args)
        filtered = gramex.data.filter('mysql://server/db', table='table', args=handler.args)

    It accepts the following parameters:

    :arg source url: Pandas DataFrame, sqlalchemy URL, directory or file name,
        http(s) data file, all `.format``-ed using ``args``.
    :arg dict args: URL query parameters as a dict of lists. Pass handler.args or parse_qs results
    :arg dict meta: this dict is updated with metadata during the course of filtering
    :arg str engine: over-rides the auto-detected engine. Can be 'dataframe', 'file',
        'http', 'https', 'sqlalchemy', 'dir'
    :arg str ext: file extension (if url is a file). Defaults to url extension
    :arg dict columns: database column names to create if required (if url is a database).
        Keys are column names. Values can be SQL types, or dicts with these keys:
            - ``type`` (str), e.g. ``"VARCHAR(10)"``
            - ``default`` (str/int/float/bool), e.g. ``"none@example.org"``
            - ``nullable`` (bool), e.g. ``False``
            - ``primary_key`` (bool), e.g. ``True`` -- used only when creating new tables
            - ``autoincrement`` (bool), e.g. ``True`` -- used only when creating new tables
    :arg str query: optional SQL query to execute (if url is a database),
        ``.format``-ed using ``args`` and supports SQLAlchemy SQL parameters.
        Loads entire result in memory before filtering.
    :arg str queryfile: optional SQL query file to execute (if url is a database).
        Same as specifying the ``query:`` in a file. Overrides ``query:``
    :arg function transform: optional in-memory transform of source data. Takes
        the result of gramex.cache.open or gramex.cache.query. Must return a
        DataFrame. Applied to both file and SQLAlchemy urls.
    :arg dict transform_kwargs: optional keyword arguments to be passed to the
        transform function -- apart from data
    :arg dict kwargs: Additional parameters are passed to
        :py:func:`gramex.cache.open` or ``sqlalchemy.create_engine``
    :return: a filtered DataFrame

    Remaining kwargs are passed to :py:func:`gramex.cache.open` if ``url`` is a file, or
    ``sqlalchemy.create_engine`` if ``url`` is a SQLAlchemy URL. In particular:

    :arg str table: table name (if url is an SQLAlchemy URL), ``.format``-ed
        using ``args``.

    If this is used in a handler as::

        filtered = gramex.data.filter(dataframe, args=handler.args)

    ... then calling the handler with ``?x=1&y=2`` returns all rows in
    ``dataframe`` where x is 1 and y is 2.

    If a table or query is passed to an SQLAlchemy url, it is formatted using
    ``args``. For example::

        data = gramex.data.filter('mysql://server/db', table='{xxx}', args=handler.args)

    ... when passed ``?xxx=sales`` returns rows from the sales table. Similarly::

        data = gramex.data.filter('mysql://server/db', args=handler.args,
                                  query='SELECT {col}, COUNT(*) FROM table GROUP BY {col}')

    ... when passsed ``?col=City`` replaces ``{col}`` with ``City``.

    **NOTE**: To avoid SQL injection attacks, only values without spaces are
    allowed. So ``?col=City Name`` or ``?col=City+Name`` **will not** work.

    The URL supports operators filter like this:

    - ``?x`` selects x is not null
    - ``?x!`` selects x is null
    - ``?x=val`` selects x == val
    - ``?x!=val`` selects x != val
    - ``?x>=val`` selects x > val
    - ``?x>~=val`` selects x >= val
    - ``?x<=val`` selects x < val
    - ``?x<~=val`` selects x <= val
    - ``?x~=val`` selects x matches val as a regular expression
    - ``?x!~=val`` selects x does not match val as a regular expression

    Multiple filters are combined into an AND clause. Ranges can also be
    specified like this:

    - ``?x=a&y=b`` selects x = a AND y = b
    - ``?x>=100&x<=200`` selects x > 100 AND x < 200

    If the same column has multiple values, they are combined like this:

    - ``?x=a&x=b`` selects x IN (a, b)
    - ``?x!=a&x!=b`` selects x NOT IN (a, b)
    - ``?x~=a&x~=b`` selects x ~ a|b
    - ``?x>=a&x>=b`` selects x > MIN(a, b)
    - ``?x<=a&x<=b`` selects x < MAX(a, b)

    Arguments are converted to the type of the column before comparing. If this
    fails, it raises a ValueError.

    These URL query parameters control the output:

    - ``?_sort=col`` sorts column col in ascending order. ``?_sort=-col`` sorts
      in descending order.
    - ``?_limit=100`` limits the result to 100 rows
    - ``?_offset=100`` starts showing the result from row 100. Default: 0
    - ``?_c=x&_c=y`` returns only columns ``[x, y]``. ``?_c=-col`` drops col.

    If a column name matches one of the above, you cannot filter by that column.
    Avoid column names beginning with _.

    To get additional information about the filtering, use::

        meta = {}      # Create a variable which will be filled with more info
        filtered = gramex.data.filter(data, meta=meta, **handler.args)

    The ``meta`` variable is populated with the following keys:

    - ``filters``: Applied filters as ``[(col, op, val), ...]``
    - ``ignored``: Ignored filters as ``[(col, vals), ('_sort', col), ('_by', col), ...]``
    - ``excluded``: Excluded columns as ``[col, ...]``
    - ``sort``: Sorted columns as ``[(col, True), ...]``. The second parameter is ``ascending=``
    - ``offset``: Offset as integer. Defaults to 0
    - ``limit``: Limit as integer - ``None`` if limit is not applied
    - ``count``: Total number of rows, if available
    - ``by``: Group by columns as ``[col, ...]``
    - ``inserted``: List of (dict of primary values) for each inserted row

    These variables may be useful to show additional information about the
    filtered data.
    '''
    # Auto-detect engine.
    if engine is None:
        engine = get_engine(url)

    # Pass the meta= argument from kwargs (if any)
    meta.update({
        'filters': [],      # Applied filters as [(col, op, val), ...]
        'ignored': [],      # Ignored filters as [(col, vals), ...]
        'sort': [],         # Sorted columns as [(col, asc), ...]
        'offset': 0,        # Offset as integer
        'limit': None,      # Limit as integer - None if not applied
        'by': [],           # Group by columns as [col, ...]
    })
    controls = _pop_controls(args)
    transform = _transform_fn(transform, transform_kwargs)
    url, ext, query, queryfile, kwargs = _replace(
        engine, args, url, ext, query, queryfile, **kwargs)

    # Use the appropriate filter function based on the engine
    if engine == 'dataframe':
        data = transform(url) if callable(transform) else url
        return _filter_frame(data, meta=meta, controls=controls, args=args)
    elif engine == 'dir':
        data = dirstat(url, **args)
        data = transform(data) if callable(transform) else data
        return _filter_frame(data, meta=meta, controls=controls, args=args)
    elif engine in {'file', 'http', 'https'}:
        if engine == 'file' and not os.path.exists(url):
            raise OSError('url: %s not found' % url)
        # Get the full dataset. Then filter it
        data = gramex.cache.open(url, ext, transform=transform, **kwargs)
        return _filter_frame(data, meta=meta, controls=controls, args=args)
    elif engine == 'sqlalchemy':
        table = kwargs.pop('table', None)
        state = kwargs.pop('state', None)
        engine = alter(url, table, columns, **kwargs)
        if query or queryfile:
            if queryfile:
                query = gramex.cache.open(queryfile, 'text')
            if not state:
                if isinstance(table, six.string_types):
                    state = table if ' ' in table else [table]
                elif isinstance(table, (list, tuple)):
                    state = [t for t in table]
                elif table is not None:
                    raise ValueError('table: must be string or list of strings, not %r' % table)
            all_params = {k: v[0] for k, v in args.items() if len(v) > 0}
            data = gramex.cache.query(sa.text(query), engine, state, params=all_params)
            data = transform(data) if callable(transform) else data
            return _filter_frame(data, meta=meta, controls=controls, args=args)
        elif table:
            if callable(transform):
                data = gramex.cache.query(table, engine, [table])
                return _filter_frame(transform(data), meta=meta, controls=controls, args=args)
            else:
                return _filter_db(engine, table, meta=meta, controls=controls, args=args)
        else:
            raise ValueError('No table: or query: specified')
    else:
        raise ValueError('engine: %s invalid. Can be sqlalchemy|file|dataframe' % engine)


def delete(url, meta={}, args=None, engine=None, table=None, ext=None, id=None, columns=None,
           query=None, queryfile=None, transform=None, transform_kwargs={}, **kwargs):
    '''
    Deletes data using URL query parameters. Typical usage::

        count = gramex.data.delete(dataframe, args=handler.args, id=['id'])
        count = gramex.data.delete('file.csv', args=handler.args, id=['id'])
        count = gramex.data.delete('mysql://server/db', table='x', args=handler.args, id=['id'])

    ``id`` is a list of column names defining the primary key.
    Calling this in a handler with ``?id=1&id=2`` deletes rows with id is 1 or 2.

    It accepts the same parameters as :py:func:`filter`, and returns the number
    of deleted rows.
    '''
    if engine is None:
        engine = get_engine(url)
    meta.update({'filters': [], 'ignored': []})
    controls = _pop_controls(args)
    url, table, ext, query, queryfile, kwargs = _replace(
        engine, args, url, table, ext, query, queryfile, **kwargs)
    if engine == 'dataframe':
        data_filtered = _filter_frame(url, meta=meta, controls=controls,
                                      args=args, source='delete', id=id)
        return len(data_filtered)
    elif engine == 'file':
        data = gramex.cache.open(url, ext, transform=transform, **kwargs)
        data_filtered = _filter_frame(data, meta=meta, controls=controls,
                                      args=args, source='delete', id=id)
        gramex.cache.save(data, url, ext, index=False, **kwargs)
        return len(data_filtered)
    elif engine == 'sqlalchemy':
        if table is None:
            raise ValueError('No table: specified')
        engine = alter(url, table, columns, **kwargs)
        return _filter_db(engine, table, meta=meta, controls=controls, args=args,
                          source='delete', id=id)
    else:
        raise ValueError('engine: %s invalid. Can be sqlalchemy|file|dataframe' % engine)


def update(url, meta={}, args=None, engine=None, table=None, ext=None, id=None, columns=None,
           query=None, queryfile=None, transform=None, transform_kwargs={}, **kwargs):
    '''
    Update data using URL query parameters. Typical usage::

        count = gramex.data.update(dataframe, args=handler.args, id=['id'])
        count = gramex.data.update('file.csv', args=handler.args, id=['id'])
        count = gramex.data.update('mysql://server/db', table='x', args=handler.args, id=['id'])

    ``id`` is a list of column names defining the primary key.
    Calling this in a handler with ``?id=1&x=2`` updates x=2 where id=1.

    It accepts the same parameters as :py:func:`filter`, and returns the number of updated rows.
    '''
    if engine is None:
        engine = get_engine(url)
    meta.update({'filters': [], 'ignored': []})
    controls = _pop_controls(args)
    url, table, ext, query, queryfile, kwargs = _replace(
        engine, args, url, table, ext, query, queryfile, **kwargs)
    if engine == 'dataframe':
        data_updated = _filter_frame(
            url, meta=meta, controls=controls, args=args, source='update', id=id)
        return len(data_updated)
    elif engine == 'file':
        data = gramex.cache.open(url, ext, transform=transform, **kwargs)
        data_updated = _filter_frame(
            data, meta=meta, controls=controls, args=args, source='update', id=id)
        gramex.cache.save(data, url, ext, index=False, **kwargs)
        return len(data_updated)
    elif engine == 'sqlalchemy':
        if table is None:
            raise ValueError('No table: specified')
        engine = alter(url, table, columns, **kwargs)
        return _filter_db(engine, table, meta=meta, controls=controls, args=args,
                          source='update', id=id)
    else:
        raise ValueError('engine: %s invalid. Can be sqlalchemy|file|dataframe' % engine)


def insert(url, meta={}, args=None, engine=None, table=None, ext=None, id=None, columns=None,
           query=None, queryfile=None, transform=None, transform_kwargs={}, **kwargs):
    '''
    Insert data using URL query parameters. Typical usage::

        count = gramex.data.insert(dataframe, args=handler.args, id=['id'])
        count = gramex.data.insert('file.csv', args=handler.args, id=['id'])
        count = gramex.data.insert('mysql://server/db', table='x', args=handler.args, id=['id'])

    ``id`` is a list of column names defining the primary key.
    Calling this in a handler with ``?id=3&x=2`` inserts a new record with id=3 and x=2.

    If the target file / table does not exist, it is created.

    It accepts the same parameters as :py:func:`filter`, and returns the number of updated rows.
    '''
    if engine is None:
        engine = get_engine(url)
    _pop_controls(args)
    if not args:
        raise ValueError('No args: specified')
    meta.update({'filters': [], 'ignored': [], 'inserted': []})
    # If values do not have equal number of elements, pad them and warn
    rowcount = max(len(val) for val in args.values())
    for key, val in args.items():
        rows = len(val)
        if 0 < rows < rowcount:
            val += [val[-1]] * (rowcount - rows)
            app_log.warning('data.insert: column %s has %d rows not %d. Extended last value %s',
                            key, rows, rowcount, val[-1])
    rows = pd.DataFrame.from_dict(args)
    url, table, ext, query, queryfile, kwargs = _replace(
        engine, args, url, table, ext, query, queryfile, **kwargs)
    if engine == 'dataframe':
        rows = _pop_columns(rows, url.columns, meta['ignored'])
        url = url.append(rows, sort=False)
        return len(rows)
    elif engine == 'file':
        try:
            data = gramex.cache.open(url, ext, transform=None, **kwargs)
        except (OSError, IOError):
            data = rows
        else:
            rows = _pop_columns(rows, data.columns, meta['ignored'])
            data = data.append(rows, sort=False)
        gramex.cache.save(data, url, ext, index=False, **kwargs)
        return len(rows)
    elif engine == 'sqlalchemy':
        if table is None:
            raise ValueError('No table: specified')
        engine = alter(url, table, columns, **kwargs)
        try:
            cols = get_table(engine, table).columns
        except sa.exc.NoSuchTableError:
            pass
        else:
            rows = _pop_columns(rows, [col.name for col in cols], meta['ignored'])
        if '.' in table:
            kwargs['schema'], table = table.rsplit('.', 1)
        # If the DB doesn't yet have the table, create it WITH THE PRIMARY KEYS.
        # Note: pandas does not document engine.dialect.has_table so it might change.
        if not engine.dialect.has_table(engine, table) and id:
            engine.execute(pd.io.sql.get_schema(rows, name=table, keys=id, con=engine))

        def insert_method(tbl, conn, keys, data_iter):
            '''Pandas .to_sql() doesn't return inserted row primary keys. Capture it in meta'''
            data = [dict(zip(keys, row)) for row in data_iter]
            # If the ?id= is not provided, Pandas creates a schema based on available columns,
            # without the `id` column. SQLAlchemy won't return inserted_primary_key unless the
            # metadata has a primary key. So, hoping that the table already has a primary key,
            # load table from DB via extend_existing=True.
            sa_table = sa.Table(table, tbl.table.metadata,
                                extend_existing=True, autoload_with=engine)
            r = conn.execute(sa_table.insert(), data)
            # SQLAlchemy 1.4+ supports inserted_primary_key_rows, but is in beta (Nov 2020).
            # ids = getattr(r, 'inserted_primary_key_rows', [])
            # If we have SQLAlchemy 1.3, only single inserts have an inserted_primary_key.
            ids = [r.inserted_primary_key] if hasattr(r, 'inserted_primary_key') else []
            # Add non-empty IDs as a dict with associated keys
            id_cols = [col.name for col in sa_table.primary_key]
            for row in ids:
                if row:
                    meta['inserted'].append(dict(zip(id_cols, row)))

        kwargs['method'] = insert_method
        # If user passes ?col= with empty value, replace with NULL. If the column is an INT/FLOAT,
        # type conversion int('') / float('') will fail.
        rows.replace('', None, inplace=True)
        pd.io.sql.to_sql(rows, table, engine, if_exists='append', index=False, **kwargs)
        return len(rows)
    else:
        raise ValueError('engine: %s invalid. Can be sqlalchemy|file|dataframe' % engine)


def get_engine(url):
    '''
    Used to detect type of url passed. Returns:

    - ``'dataframe'`` if url is a Pandas DataFrame
    - ``'sqlalchemy'`` if url is a sqlalchemy compatible URL
    - ``protocol`` if url is of the form `protocol://...`
    - ``'dir'`` if it is not a URL but a valid directory
    - ``'file'`` if it is not a URL but a valid file

    Else it raises an Exception
    '''
    if isinstance(url, pd.DataFrame):
        return 'dataframe'
    try:
        url = sa.engine.url.make_url(url)
    except sa.exc.ArgumentError:
        return 'dir' if os.path.isdir(url) else 'file'
    try:
        url.get_driver_name()
        return 'sqlalchemy'
    except sa.exc.NoSuchModuleError:
        return url.drivername


def create_engine(url, **kwargs):
    '''
    Cached version of sqlalchemy.create_engine.

    Normally, this is not required. But :py:func:`get_table` caches the engine
    *and* metadata *and* uses autoload=True. This makes sqlalchemy create a new
    database connection for every engine object, and not dispose it. So we
    re-use the engine objects within this module.
    '''
    if url not in _ENGINE_CACHE:
        _ENGINE_CACHE[url] = sa.create_engine(url, **kwargs)
    return _ENGINE_CACHE[url]


def get_table(engine, table, **kwargs):
    '''Return the sqlalchemy table from the engine and table name'''
    if engine not in _METADATA_CACHE:
        _METADATA_CACHE[engine] = sa.MetaData(bind=engine)
    metadata = _METADATA_CACHE[engine]
    if '.' in table:
        kwargs['schema'], table = table.rsplit('.', 1)
    return sa.Table(table, metadata, autoload=True, autoload_with=engine, **kwargs)


def _pop_controls(args):
    '''Filter out data controls: sort, limit, offset and column (_c) from args'''
    return {
        key: args.pop(key)
        for key in ('_sort', '_limit', '_offset', '_c', '_by')
        if key in args
    }


def _pop_columns(data, cols, ignored):
    '''Remove columns not in cols'''
    cols = set(cols)
    for col in data.columns:
        if col not in cols:
            ignored.append([col, data[col].tolist()])
    return data[[col for col in cols if col in data.columns]]


def _sql_safe(val):
    '''Return True if val is safe for insertion in an SQL query'''
    if isinstance(val, six.string_types):
        return not re.search(r'\s', val)
    elif isinstance(val, six.integer_types) or isinstance(val, (float, bool)):
        return True
    return False


def _path_safe(path):
    '''Returns True if path does not try to escape outside a given directory using .. or / etc'''
    # Ignore non-strings. These are generally not meant for paths
    if not isinstance(path, six.string_types):
        return True
    return os.path.realpath(os.path.join(_path_safe_root, path)).startswith(_path_safe_root)


# The order of operators is important. ~ is at the end. Otherwise, !~
# or >~ will also be mapped to ~ as an operator
operators = ['!', '>', '>~', '<', '<~', '!~', '~']


def _filter_col(col, cols):
    '''
    Parses a column name from a list of columns and returns a (col, agg, op)
    tuple.

    - ``col`` is the name of the column in cols.
    - ``agg`` is the aggregation operation (SUM, MIN, MAX, etc), else None
    - ``op`` is the operator ('', !, >, <, etc)

    If the column is invalid, then ``col`` and ``op`` are None
    '''
    colset = set(cols)
    # ?col= is returned quickly
    if col in colset:
        return col, None, ''
    # Check if it matches a non-empty operator, like ?col>~=
    for op in operators:
        if col.endswith(op):
            name = col[:-len(op)]
            if name in colset:
                return name, None, op
            # If there's an aggregator, split it out, like ?col|SUM>~=
            elif _agg_sep in name:
                name, agg = name.rsplit(_agg_sep, 1)
                if name in colset:
                    return name, agg, op
    # If no operators match, it might be a pure aggregation, like ?col|SUM=
    if _agg_sep in col:
        name, agg = col.rsplit(_agg_sep, 1)
        if name in colset:
            return name, agg, ''
    # Otherwise we don't know what it is
    return None, None, None


def _filter_frame_col(data, key, col, op, vals, meta):
    # Apply type conversion for values
    conv = data[col].dtype.type
    vals = tuple(conv(val) for val in vals if val)
    if op not in {'', '!'} and len(vals) == 0:
        meta['ignored'].append((key, vals))
    elif op == '':
        data = data[data[col].isin(vals)] if len(vals) else data[pd.notnull(data[col])]
    elif op == '!':
        data = data[~data[col].isin(vals)] if len(vals) else data[pd.isnull(data[col])]
    elif op == '>':
        data = data[data[col] > min(vals)]
    elif op == '>~':
        data = data[data[col] >= min(vals)]
    elif op == '<':
        data = data[data[col] < max(vals)]
    elif op == '<~':
        data = data[data[col] <= max(vals)]
    elif op == '!~':
        data = data[~data[col].str.contains('|'.join(vals))]
    elif op == '~':
        data = data[data[col].str.contains('|'.join(vals))]
    meta['filters'].append((col, op, vals))
    return data


def _filter_db_col(query, method, key, col, op, vals, column, conv, meta):
    '''
    - Updates ``query`` with a method (WHERE/HAVING) that sets '<key> <op> <vals>'
    - ``column`` is the underlying ColumnElement
    - ``conv`` is a type conversion function that converts ``vals`` to the correct type
    - Updates ``meta`` with the fields used for filtering (or ignored)
    '''
    # In PY2, .python_type returns str. We want unicode
    sql_types = {six.binary_type: six.text_type, pd.datetime: six.text_type}
    conv = sql_types.get(conv, conv)
    vals = tuple(conv(val) for val in vals if val)
    if op not in {'', '!'} and len(vals) == 0:
        meta['ignored'].append((key, vals))
    elif op == '':
        # Test if column is not NULL. != None is NOT the same as is not None
        query = method(column.in_(vals) if len(vals) else column != None)      # noqa
    elif op == '!':
        # Test if column is NULL. == None is NOT the same as is None
        query = method(column.notin_(vals) if len(vals) else column == None)   # noqa
    elif op == '>':
        query = method(column > min(vals))
    elif op == '>~':
        query = method(column >= min(vals))
    elif op == '<':
        query = method(column < max(vals))
    elif op == '<~':
        query = method(column <= max(vals))
    elif op == '!~':
        query = method(column.notlike('%' + '%'.join(vals) + '%'))
    elif op == '~':
        query = method(column.like('%' + '%'.join(vals) + '%'))
    meta['filters'].append((col, op, vals))
    return query


def _filter_sort_columns(sort_filter, cols):
    sorts, ignore_sorts = [], []
    for col in sort_filter:
        if col in cols:
            sorts.append((col, True))
        elif col.startswith('-') and col[1:] in cols:
            sorts.append((col[1:], False))
        else:
            ignore_sorts.append(col)
    return sorts, ignore_sorts


def _filter_select_columns(col_filter, cols, meta):
    '''
    Checks ?_c=col&_c=-col for filter(). Takes values of ?_c= as col_filter and
    data column names as cols. Returns 2 lists: show_cols as columns to show.
    ignored_cols has column names not in the list, i.e. the ?_c= parameters that
    are ignored.
    '''
    selected_cols, excluded_cols, ignored_cols = [], set(), []
    for col in col_filter:
        if col in cols:
            selected_cols.append(col)
        elif col.startswith('-') and col[1:] in cols:
            excluded_cols.add(col[1:])
        else:
            ignored_cols.append(col)
    if len(excluded_cols) > 0 and len(selected_cols) == 0:
        selected_cols = cols
    show_cols = [col for col in selected_cols if col not in excluded_cols]
    meta['excluded'] = list(excluded_cols)
    return show_cols, ignored_cols


def _filter_groupby_columns(by, cols, meta):
    '''
    Checks ?_by=col&_by=col for filter().

    - ``by``: list of column names to group by
    - ``cols``: list of valid column names
    - ``meta``: meta['by'] and meta['ignored'] are updated

    Returns a list of columns to group by
    '''
    colset = set(cols)
    for col in by:
        if col in colset:
            meta['by'].append(col)
        else:
            meta['ignored'].append(('_by', col))
    return meta['by']


# If ?by=col|avg is provided, this works in SQL but not in Pandas DataFrames.
# Convert into a DataFrame friendly function
_frame_functions = {
    'avg': 'mean',
    'average': 'mean',
}


def _filter_frame(data, meta, controls, args, source='select', id=[]):
    '''
    If ``source`` is ``'select'``, returns a DataFrame in which the DataFrame
    ``data`` is filtered using ``args``. Additional controls like _sort, etc are
    in ``controls``. Metadata is stored in ``meta``.

    If ``source`` is ``'update'``, filters using ``args`` but only for columns
    mentioned in ``id``. Resulting DataFrame is updated with remaining ``args``.
    Returns the updated rows.

    If ``source`` is ``'delete'``, filters using ``args`` but only for columns
    mentioned in ``id``. Deletes these rows. Returns the deleted rows.

    :arg data: dataframe
    :arg meta: dictionary of `filters`, `ignored`, `sort`, `offset`, `limit` params from kwargs
    :arg args: user arguments to filter the data
    :arg source: accepted values - `update`, `delete` for PUT, DELETE methods in FormHandler
    :arg id: list of id specific to data using which values can be updated
    '''
    original_data = data
    cols_for_update = {}
    cols_having = []
    for key, vals in args.items():
        # check if `key`` is in the `id` list -- ONLY when data is updated
        if (source in ('update', 'delete') and key in id) or (source == 'select'):
            # Parse column names, ignoring missing / unmatched columns
            col, agg, op = _filter_col(key, data.columns)
            if col is None:
                meta['ignored'].append((key, vals))
                continue
            # Process aggregated columns AFTER filtering, not before (like HAVING clause)
            # e.g. ?sales|SUM=<val> should be applied only after the column is created
            if agg is not None:
                cols_having.append((key, col + _agg_sep + agg, op, vals))
                continue
            # Apply filters
            data = _filter_frame_col(data, key, col, op, vals, meta)
        elif source == 'update':
            # Update values should only contain 1 value. 2nd onwards are ignored
            if key not in data.columns or len(vals) == 0:
                meta['ignored'].append((key, vals))
            else:
                cols_for_update[key] = vals[0]
                if len(vals) > 1:
                    meta['ignored'].append((key, vals[1:]))
        else:
            meta['ignored'].append((key, vals))
    meta['count'] = len(data)
    if source == 'delete':
        original_data.drop(data.index, inplace=True)
        return data
    elif source == 'update':
        conv = {k: v.type for k, v in data.dtypes.items()}
        for key, val in cols_for_update.items():
            original_data.loc[data.index, key] = conv[key](val)
        return data
    else:
        # Apply controls
        if '_by' in controls:
            by = _filter_groupby_columns(controls['_by'], data.columns, meta)
            # If ?_c is not specified, use 'col|sum' for all numeric columns
            # TODO: This does not support ?_c=-<col> to hide a column
            col_list = controls.get('_c', None)
            if col_list is None:
                col_list = [col + _agg_sep + 'sum' for col in data.columns      # noqa
                            if pd.api.types.is_numeric_dtype(data[col])]
            agg_cols = []
            agg_dict = AttrDict()
            for key in col_list:
                col, agg, val = _filter_col(key, data.columns)
                if agg is not None:
                    # Convert aggregation into a Pandas GroupBy agg function
                    agg = agg.lower()
                    agg = _frame_functions.get(agg, agg)
                    agg_cols.append(key)
                    if col in agg_dict:
                        agg_dict[col].append(agg)
                    else:
                        agg_dict[col] = [agg]
            if len(by) > 0:
                if not agg_cols:
                    # If no aggregation columns exist, just show groupby columns.
                    data = data.groupby(by).agg('size').reset_index()
                    data = data.iloc[:, [0]]
                else:
                    data = data.groupby(by).agg(agg_dict)
                    data.columns = agg_cols
                    data = data.reset_index()
                # Apply HAVING operators
                for key, col, op, vals in cols_having:
                    data = _filter_frame_col(data, key, col, op, vals, meta)
            else:
                row = [data[col].agg(op) for col, ops in agg_dict.items() for op in ops]
                data = pd.DataFrame([row], columns=agg_cols)
        elif '_c' in controls:
            show_cols, hide_cols = _filter_select_columns(controls['_c'], data.columns, meta)
            data = data[show_cols]
            if len(hide_cols) > 0:
                meta['ignored'].append(('_c', hide_cols))
        if '_sort' in controls:
            meta['sort'], ignore_sorts = _filter_sort_columns(controls['_sort'], data.columns)
            if len(meta['sort']) > 0:
                data = data.sort_values(by=[c[0] for c in meta['sort']],
                                        ascending=[c[1] for c in meta['sort']])
            if len(ignore_sorts) > 0:
                meta['ignored'].append(('_sort', ignore_sorts))
        if '_offset' in controls:
            try:
                offset = min(int(v) for v in controls['_offset'])
            except ValueError:
                raise ValueError('_offset not integer: %r' % controls['_offset'])
            data = data.iloc[offset:]
            meta['offset'] = offset
        if '_limit' in controls:
            try:
                limit = min(int(v) for v in controls['_limit'])
            except ValueError:
                raise ValueError('_limit not integer: %r' % controls['_limit'])
            data = data.iloc[:limit]
            meta['limit'] = limit
        return data


def _filter_db(engine, table, meta, controls, args, source='select', id=[]):
    '''

    It accepts the following parameters

    :arg sqlalchemy engine engine: constructed sqlalchemy string
    :arg database table table: table name in the mentioned database
    :arg controls: dictionary of `_sort`, `_c`, `_offset`, `_limit` params
    :arg meta: dictionary of `filters`, `ignored`, `sort`, `offset`, `limit` params from kwargs
    :arg args: dictionary of user arguments to filter the data
    :arg source: accepted values - `update`, `delete` for PUT, DELETE methods in FormHandler
    :arg id: list of keys specific to data using which values can be updated
    '''
    table = get_table(engine, table)
    cols = table.columns
    colslist = cols.keys()

    if source == 'delete':
        query = sa.delete(table)
    elif source == 'update':
        query = sa.update(table)
    else:
        query = sa.select([table])
    cols_for_update = {}
    cols_having = []
    for key, vals in args.items():
        # check if `key`` is in the `id` list -- ONLY when data is updated
        if (source in ('update', 'delete') and key in id) or (source == 'select'):
            # Parse column names, ignoring missing / unmatched columns
            col, agg, op = _filter_col(key, colslist)
            if col is None:
                meta['ignored'].append((key, vals))
                continue
            # Process aggregated columns AFTER filtering, not before (like HAVING clause)
            # e.g. ?sales|SUM=<val> should be applied only after the column is created
            if agg is not None:
                cols_having.append((key, col + _agg_sep + agg, op, vals))
                continue
            # Apply filters
            query = _filter_db_col(query, query.where, key, col, op, vals,
                                   cols[col], cols[col].type.python_type, meta)
        elif source == 'update':
            # Update values should only contain 1 value. 2nd onwards are ignored
            if key not in cols or len(vals) == 0:
                meta['ignored'].append((key, vals))
            else:
                cols_for_update[key] = vals[0]
                if len(vals) > 1:
                    meta['ignored'].append((key, vals[1:]))
        else:
            meta['ignored'].append((key, vals))
    if source == 'delete':
        res = engine.execute(query)
        return res.rowcount
    elif source == 'update':
        query = query.values(cols_for_update)
        res = engine.execute(query)
        return res.rowcount
    else:
        # Apply controls
        if '_by' in controls:
            by = _filter_groupby_columns(controls['_by'], colslist, meta)
            query = query.group_by(*by)
            # If ?_c is not specified, use 'col|sum' for all numeric columns
            # TODO: This does not support ?_c=-<col> to hide a column
            col_list = controls.get('_c', None)
            if col_list is None:
                col_list = [col + _agg_sep + 'sum' for col, column in cols.items()  # noqa
                            if column.type.python_type.__name__ in _numeric_types]
            agg_cols = AttrDict([(col, cols[col]) for col in by])   # {label: ColumnElement}
            typ = {}                                                # {label: python type}
            for key in col_list:
                col, agg, val = _filter_col(key, colslist)
                if agg is not None:
                    # Convert aggregation into SQLAlchemy query
                    agg = agg.lower()
                    typ[key] = _agg_type.get(agg, cols[col].type.python_type)
                    agg_func = getattr(sa.sql.expression.func, agg)
                    agg_cols[key] = agg_func(cols[col]).label(key)
            if not agg_cols:
                return pd.DataFrame()
            query = query.with_only_columns(agg_cols.values())
            # Apply HAVING operators
            for key, col, op, vals in cols_having:
                query = _filter_db_col(query, query.having, key, col, op, vals,
                                       agg_cols[col], typ[col], meta)
        elif '_c' in controls:
            show_cols, hide_cols = _filter_select_columns(controls['_c'], colslist, meta)
            query = query.with_only_columns([cols[col] for col in show_cols])
            if len(hide_cols) > 0:
                meta['ignored'].append(('_c', hide_cols))
            if len(show_cols) == 0:
                return pd.DataFrame()
        if '_sort' in controls:
            meta['sort'], ignore_sorts = _filter_sort_columns(
                controls['_sort'], colslist + query.columns.keys())
            for col, asc in meta['sort']:
                orderby = sa.asc if asc else sa.desc
                query = query.order_by(orderby(col))
            if len(ignore_sorts) > 0:
                meta['ignored'].append(('_sort', ignore_sorts))
        if '_offset' in controls:
            try:
                offset = min(int(v) for v in controls['_offset'])
            except ValueError:
                raise ValueError('_offset not integer: %r' % controls['_offset'])
            query = query.offset(offset)
            meta['offset'] = offset
        if '_limit' in controls:
            try:
                limit = min(int(v) for v in controls['_limit'])
            except ValueError:
                raise ValueError('_limit not integer: %r' % controls['_limit'])
            query = query.limit(limit)
            meta['limit'] = limit
        return pd.read_sql(query, engine)


_VEGA_SCRIPT = os.path.join(_FOLDER, 'download.vega.js')


def download(data, format='json', template=None, args={}, **kwargs):
    '''
    Download a DataFrame or dict of DataFrames in various formats. This is used
    by :py:class:`gramex.handlers.FormHandler`. You are **strongly** advised to
    try it before creating your own FunctionHandler.

    Usage as a FunctionHandler::

        def download_as_csv(handler):
            handler.set_header('Content-Type', 'text/csv')
            handler.set_header('Content-Disposition', 'attachment;filename=data.csv')
            return gramex.data.download(dataframe, format='csv')

    It takes the following arguments:

    :arg dataset data: A DataFrame or a dict of DataFrames
    :arg str format: Output format. Can be ``csv|json|html|xlsx|template``
    :arg file template: Path to template file for ``template`` format
    :arg dict args: dictionary of user arguments to subsitute spec
    :arg dict kwargs: Additional parameters that are passed to the relevant renderer
    :return: bytes with the download file contents

    When ``data`` is a DataFrame, this is what different ``format=`` parameters
    return:

    - ``csv`` returns a UTF-8-BOM encoded CSV file of the dataframe
    - ``xlsx`` returns an Excel file with 1 sheet named ``data``. kwargs are
      passed to ``.to_excel(index=False)``
    - ``html`` returns a HTML file with a single table. kwargs are passed to
      ``.to_html(index=False)``
    - ``json`` returns a JSON file. kwargs are passed to
      ``.to_json(orient='records', force_ascii=True)``.
    - ``template`` returns a Tornado template rendered file. The template
      receives ``data`` as ``data`` and any additional kwargs.
    - ``pptx`` returns a PPTX generated by pptgen
    - ``seaborn`` or ``sns`` returns a Seaborn generated chart
    - ``vega`` returns JavaScript that renders a Vega chart

    When ``data`` is a dict of DataFrames, the following additionally happens:

    - ``format='csv'`` renders all DataFrames one below the other, adding the
      key as heading
    - ``format='xlsx'`` renders each DataFrame on a sheet whose name is the key
    - ``format='html'`` renders tables below one another with the key as heading
    - ``format='json'`` renders as a dict of DataFrame JSONs
    - ``format='template'`` sends ``data`` and all ``kwargs`` as passed to the
      template
    - ``format='pptx'`` passes ``data`` as a dict of datasets to pptgen
    - ``format='vega'`` passes ``data`` as a dict of datasets to Vega

    You need to set the MIME types on the handler yourself. Recommended MIME
    types are in gramex.yaml under handler.FormHandler.
    '''
    if isinstance(data, dict):
        for key, val in data.items():
            if not isinstance(val, pd.DataFrame):
                raise ValueError('download({"%s": %r}) invalid type' % (key, type(val)))
        if not len(data):
            raise ValueError('download() data requires at least 1 DataFrame')
        multiple = True
    elif not isinstance(data, pd.DataFrame):
        raise ValueError('download(%r) invalid type' % type(data))
    else:
        data = {'data': data}
        multiple = False

    def kw(**conf):
        return merge(kwargs, conf, mode='setdefault')

    if format == 'csv':
        # csv.writer requires BytesIO in PY2 and StringIO in PY3.
        # I can't see an elegant way out of this other than writing code for each.
        if six.PY2:
            out = io.BytesIO()
            kw(index=False, encoding='utf-8')
            for index, (key, val) in enumerate(data.items()):
                if index > 0:
                    out.write(b'\n')
                if multiple:
                    out.write(key.encode('utf-8') + b'\n')
                val.to_csv(out, **kwargs)
            result = out.getvalue()
            # utf-8-sig encoding returns the result with a UTF-8 BOM. Easier to open in Excel
            return ''.encode('utf-8-sig') + result if result.strip() else result
        else:
            out = io.StringIO()
            kw(index=False)
            for index, (key, val) in enumerate(data.items()):
                if index > 0:
                    out.write('\n')
                if multiple:
                    out.write(key + '\n')
                val.to_csv(out, **kwargs)
            result = out.getvalue()
            # utf-8-sig encoding returns the result with a UTF-8 BOM. Easier to open in Excel
            return result.encode('utf-8-sig') if result.strip() else result.encode('utf-8')
    elif format == 'template':
        return gramex.cache.open(template, 'template').generate(
            data=data if multiple else data['data'], **kwargs)
    elif format == 'html':
        out = io.StringIO()
        kw(index=False)
        for key, val in data.items():
            if multiple:
                out.write('<h1>%s</h1>' % key)
            val.to_html(out, **kwargs)
        return out.getvalue().encode('utf-8')
    elif format in {'xlsx', 'xls'}:
        out = io.BytesIO()
        kw(index=False)
        # TODO: Create and use a FrameWriter for formatting
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            for key, val in data.items():
                val.to_excel(writer, sheet_name=key, **kwargs)
        return out.getvalue()
    elif format in {'pptx', 'ppt'}:
        from gramex.pptgen import pptgen    # noqa
        out = io.BytesIO()
        pptgen(target=out, data=data, **kwargs)
        return out.getvalue()
    elif format in {'seaborn', 'sns'}:
        kw = AttrDict()
        defaults = {'chart': 'barplot', 'ext': 'png', 'data': 'data', 'dpi': 96,
                    'width': 640, 'height': 480}
        for key, default in defaults.items():
            kw[key] = kwargs.pop(key, default)
        import matplotlib
        matplotlib.use('Agg')       # Before importing seaborn, set a headless backend
        import seaborn as sns
        plot = getattr(sns, kw.chart)(data=data.get(kw.data), **kwargs)
        out = io.BytesIO()
        fig = plot.figure if hasattr(plot, 'figure') else plot.fig
        for k in ['dpi', 'width', 'height']:
            kw[k] = float(kw[k])
        fig.set_size_inches(kw.width / kw.dpi, kw.height / kw.dpi)
        fig.savefig(out, format=kw.ext, dpi=kw.dpi)
        fig.clear()
        return out.getvalue()
    elif format in {'vega', 'vega-lite', 'vegam'}:
        kwargs = kw(orient='records', force_ascii=True)
        spec = kwargs.pop('spec', {})
        kwargs.pop('handler', None)
        out = io.BytesIO()
        # conf = {..., spec: {..., data: __DATA__}}
        if isinstance(spec.get('data'), (dict, list)) or 'fromjson' in spec:
            # support only one dataset
            values = list(data.values())
            out.write(values[0].to_json(**kwargs).encode('utf-8'))
            out = out.getvalue()
        else:
            spec['data'] = '__DATA__'
            for index, (key, val) in enumerate(data.items()):
                out.write(b',{"name":' if index > 0 else b'{"name":')
                out.write(json_encode(key).encode('utf-8'))
                out.write(b',"values":')
                out.write(val.to_json(**kwargs).encode('utf-8'))
                out.write(b'}')
            out = out.getvalue()
            if format == 'vega':
                out = b'[' + out + b']'
        kwargs['spec'], _ = _replace('', args, spec)
        conf = json.dumps(kwargs, ensure_ascii=True, separators=(',', ':'), indent=None)
        conf = conf.encode('utf-8').replace(b'"__DATA__"', out)
        script = gramex.cache.open(_VEGA_SCRIPT, 'bin')
        return script.replace(b'/*{conf}*/', conf)
    else:
        out = io.BytesIO()
        kwargs = kw(orient='records', force_ascii=True)
        if multiple:
            out.write(b'{')
            for index, (key, val) in enumerate(data.items()):
                if index > 0:
                    out.write(b',')
                out.write(json_encode(key).encode('utf-8'))
                out.write(b':')
                out.write(val.to_json(**kwargs).encode('utf-8'))
            out.write(b'}')
        else:
            out.write(data['data'].to_json(**kwargs).encode('utf-8'))
        return out.getvalue()


def dirstat(url, timeout=10, **kwargs):
    '''
    Return a DataFrame with the list of all files & directories under the url.

    It accepts the following parameters:

    :arg str url: path to a directory, or a URL like ``dir:///c:/path/``,
        ``dir:////root/dir/``. Raises ``OSError`` if url points to a missing
        location or is not a directory.
    :arg int timeout: max seconds to wait. ``None`` to wait forever. (default: 10)
    :return: a DataFrame with columns:
        - ``type``: extension with a ``.`` prefix -- or ``dir``
        - ``dir``: directory path to the file relative to the URL
        - ``name``: file name (including extension)
        - ``path``: full path to file or dir. This equals url / dir / name
        - ``size``: file size
        - ``mtime``: last modified time in seconds since epoch
        - ``level``: path depth (i.e. the number of paths in dir)
    '''
    try:
        url = sa.engine.url.make_url(url)
        target = url.database
    except sa.exc.ArgumentError:
        target = url
    if not os.path.isdir(target):
        raise OSError('dirstat: %s is not a directory' % target)
    target = os.path.normpath(target)
    result = []
    start_time = time.time()
    for dirpath, dirnames, filenames in os.walk(target):
        if timeout and time.time() - start_time > timeout:
            app_log.debug('dirstat: %s timeout (%.1fs)', url, timeout)
            break
        for name in dirnames:
            path = os.path.join(dirpath, name)
            stat = os.stat(path)
            dirname = dirpath.replace(target, '').replace(os.sep, '/') + '/'
            result.append({
                'path': path, 'dir': dirname, 'name': name, 'type': 'dir',
                'size': stat.st_size, 'mtime': stat.st_mtime, 'level': dirname.count('/'),
            })
        for name in filenames:
            path = os.path.join(dirpath, name)
            stat = os.stat(path)
            dirname = dirpath.replace(target, '').replace(os.sep, '/') + '/'
            result.append({
                'path': path, 'dir': dirname, 'name': name, 'type': os.path.splitext(name)[-1],
                'size': stat.st_size, 'mtime': stat.st_mtime, 'level': dirname.count('/'),
            })
    return pd.DataFrame(result)


def filtercols(url, args={}, meta={}, engine=None, table=None, ext=None,
               query=None, queryfile=None, transform=None, transform_kwargs={}, **kwargs):
    '''
    Filter data and extract unique values of each column using URL query parameters.
    Typical usage::

        filtered = gramex.data.filtercols(dataframe, args=handler.args)
        filtered = gramex.data.filtercols('file.csv', args=handler.args)
        filtered = gramex.data.filtercols('mysql://server/db', table='table', args=handler.args)

    It accepts the following parameters:

    :arg source url: Pandas DataFrame, sqlalchemy URL, directory or file name,
        `.format``-ed using ``args``.
    :arg dict args: URL query parameters as a dict of lists. Pass handler.args or parse_qs results
    :arg dict meta: this dict is updated with metadata during the course of filtering
    :arg str engine: over-rides the auto-detected engine. Can be 'dataframe', 'file',
        'http', 'https', 'sqlalchemy', 'dir'
    :arg str table: table name (if url is an SQLAlchemy URL), ``.format``-ed
        using ``args``.
    :arg str ext: file extension (if url is a file). Defaults to url extension
    :arg str query: optional SQL query to execute (if url is a database),
        ``.format``-ed using ``args`` and supports SQLAlchemy SQL parameters.
        Loads entire result in memory before filtering.
    :arg str queryfile: optional SQL query file to execute (if url is a database).
        Same as specifying the ``query:`` in a file. Overrides ``query:``
    :arg function transform: optional in-memory transform of source data. Takes
        the result of gramex.cache.open or gramex.cache.query. Must return a
        DataFrame. Applied to both file and SQLAlchemy urls.
    :arg dict transform_kwargs: optional keyword arguments to be passed to the
        transform function -- apart from data
    :arg dict kwargs: Additional parameters are passed to
        :py:func:`gramex.cache.open` or ``sqlalchemy.create_engine``
    :return: a filtered DataFrame

    Remaining kwargs are passed to :py:func:`gramex.cache.open` if ``url`` is a file, or
    ``sqlalchemy.create_engine`` if ``url`` is a SQLAlchemy URL.

    If this is used in a handler as::

        filtered = gramex.data.filtercols(dataframe, args=handler.args)

    ... then calling the handler with ``?_c=state&_c=district`` returns all unique values
     in columns of ``dataframe`` where columns are state and district.

    Column filter supports like this:

    - ``?_c=y&x`` returns df with unique values of y where x is not null
    - ``?_c=y&x=val`` returns df with unique values of y where x == val
    - ``?_c=y&y=val`` returns df with unique values of y, ignores filter y == val
    - ``?_c=y&x>=val`` returns df with unique values of y where x > val
    - ``?_c=x&_c=y&x=val`` returns df with unique values of x ignoring filter x == val
      and returns unique values of y where x == val

    Arguments are converted to the type of the column before comparing. If this
    fails, it raises a ValueError.

    These URL query parameters control the output:

    - ``?_sort=col`` sorts column col in ascending order. ``?_sort=-col`` sorts
      in descending order.
    - ``?_limit=100`` limits the result to 100 rows
    - ``?_offset=100`` starts showing the result from row 100. Default: 0
    - ``?_c=x&_c=y`` returns only columns ``[x, y]``. ``?_c=-col`` drops col.

    If a column name matches one of the above, you cannot filter by that column.
    Avoid column names beginning with _.

    To get additional information about the filtering, use::

        meta = {}      # Create a variable which will be filled with more info
        filtered = gramex.data.filter(data, meta=meta, **handler.args)

    The ``meta`` variable is populated with the following keys:

    - ``filters``: Applied filters as ``[(col, op, val), ...]``
    - ``ignored``: Ignored filters as ``[(col, vals), ('_sort', cols), ...]``
    - ``excluded``: Excluded columns as ``[col, ...]``
    - ``sort``: Sorted columns as ``[(col, True), ...]``. The second parameter is ``ascending=``
    - ``offset``: Offset as integer. Defaults to 0
    - ``limit``: Limit as integer - ``100`` if limit is not applied
    - ``count``: Total number of rows, if available

    These variables may be useful to show additional information about the
    filtered data.
    '''
    # Auto-detect engine.
    if engine is None:
        engine = get_engine(url)
    result = {}
    limit = args.get('_limit', [100])
    try:
        limit = min(int(v) for v in limit)
    except ValueError:
        raise ValueError('_limit not integer: %r' % limit)
    for col in args.get('_c', []):
        # col_args takes _sort, _c and all filters from args
        col_args = {}
        for key, value in args.items():
            if key in ['_sort']:
                col_args[key] = value
            # Ignore any filters on the column we are currently processing
            if not key.startswith('_') and key != col:
                col_args[key] = value
        col_args['_by'] = [col]
        col_args['_c'] = []
        col_args['_limit'] = [limit]
        result[col] = gramex.data.filter(url, table=table, args=col_args, **kwargs)
    return result


def alter(url: str, table: str, columns: dict = None, **kwargs):
    '''
    Create or alter a table with columns specified::

        gramex.data.alter(url, table, columns={
            'id': {'type': 'int', 'primary_key': True, 'autoincrement': True},
            'email': {'nullable': True, 'default': 'none'},
            'age': {'type': 'float', 'nullable': False, 'default': 18},
        })

    It accepts the following parameters:

    :arg str url: sqlalchemy URL
    :arg str table: table name
    :arg dict columns: column names, with values are SQL types, or dicts with keys:
        - ``type`` (str), e.g. ``"VARCHAR(10)"``
        - ``default`` (str/int/float/bool), e.g. ``"none@example.org"``
        - ``nullable`` (bool), e.g. ``False``
        - ``primary_key`` (bool), e.g. ``True`` -- used only when creating new tables
        - ``autoincrement`` (bool), e.g. ``True`` -- used only when creating new tables
    :return: sqlalchemy engine

    Other kwargs are passed to ``sqlalchemy.create_engine()``.

    If the table exists, any new columns are added. Existing columns are unchanged.

    If the table does not exist, the table is created with the specified columns.

    Note: ``primary_key`` and ``autoincrement`` don't work on existing tables because:
        - SQLite disallows PRIMARY KEY with ALTER. https://stackoverflow.com/a/1120030/100904
        - AUTO_INCREMENT doesn't work without PRIMARY KEY in MySQL
    '''
    engine = create_engine(url, **kwargs)
    if columns is None:
        return engine
    try:
        db_table = get_table(engine, table)
    except sa.exc.NoSuchTableError:
        # If the table's not in the DB, create it
        cols = []
        for name, row in columns.items():
            row = dict({'type': row} if isinstance(row, str) else row, name=name)
            col_type = row.get('type', 'text')
            if isinstance(col_type, str):
                # Use eval() to handle direct types like INTEGER *and* expressions like VARCHAR(3)
                row['type'] = eval(col_type.upper(), vars(sa.types))    # nosec
            row['type_'] = row.pop('type')
            if 'default' in row:
                row['server_default'] = str(row.pop('default'))
            cols.append(sa.Column(**row))
        sa.Table(table, _METADATA_CACHE[engine], *cols).create(engine)
    else:
        quote = engine.dialect.identifier_preparer.quote_identifier
        # If the table's already in the DB, add new columns. We can't change column types
        with engine.connect() as conn:
            with conn.begin():
                for name, row in columns.items():
                    if name in db_table.columns:
                        continue
                    row = {'type': row} if isinstance(row, str) else row
                    col_type = row.get('type', 'text')
                    constraints = []
                    if 'nullable' in row:
                        constraints.append('' if row['nullable'] else 'NOT NULL')
                    if 'default' in row:
                        # repr() converts int, float properly,
                        #   str into 'str' with single quotes (which is the MySQL standard)
                        #   TODO: datetime and other types will fail
                        constraints += ['DEFAULT', repr(row['default'])]
                    # This syntax works on DB2, MySQL, Oracle, PostgreSQL, SQLite
                    conn.execute(
                        f'ALTER TABLE {quote(table)} '
                        f'ADD COLUMN {quote(name)} {col_type} {" ".join(constraints)}')
        # Refresh table metadata after altering
        get_table(engine, table, extend_existing=True)
    return engine
