'''
Interact with data from the browser
'''
from __future__ import unicode_literals

import io
import os
import re
import six
import time
import json
import sqlalchemy
import pandas as pd
import gramex.cache
from tornado.escape import json_encode
from sqlalchemy.sql import text
from gramex.config import merge, app_log
from orderedattrdict import AttrDict

_METADATA_CACHE = {}
_FOLDER = os.path.dirname(os.path.abspath(__file__))
# Dummy path used by _path_safe to detect sub-directories
_path_safe_root = os.path.realpath('/root/dir')


def filter(url, args={}, meta={}, engine=None, table=None, ext=None,
           query=None, queryfile=None, transform=None, **kwargs):
    '''
    Filters data using URL query parameters. Typical usage::

        filtered = gramex.data.filter(dataframe, args=handler.args)
        filtered = gramex.data.filter('file.csv', args=handler.args)
        filtered = gramex.data.filter('mysql://server/db', table='table', args=handler.args)

    It accepts the following parameters:

    :arg source url: Pandas DataFrame, sqlalchemy URL, directory or file name,
        `.format``-ed using ``args``.
    :arg dict args: URL query parameters as a dict of lists. Pass handler.args or parse_qs results
    :arg dict meta: this dict is updated with metadata during the course of filtering
    :arg string table: table name (if url is an SQLAlchemy URL), ``.format``-ed
        using ``args``.
    :arg string ext: file extension (if url is a file). Defaults to url extension
    :arg string query: optional SQL query to execute (if url is a database),
        ``.format``-ed using ``args`` and supports SQLAlchemy SQL parameters.
        Loads entire result in memory before filtering.
    :arg string queryfile: optional SQL query file to execute (if url is a database).
        Same as specifying the ``query:`` in a file. Overrides ``query:``
    :arg function transform: optional in-memory transform of source data. Takes
        the result of gramex.cache.open or gramex.cache.query. Must return a
        DataFrame. Applied to both file and SQLAlchemy urls.
    :arg dict kwargs: Additional parameters are passed to
        :py:func:`gramex.cache.open` or ``sqlalchemy.create_engine``
    :return: a filtered DataFrame

    Remaining kwargs are passed to :py:func:`gramex.cache.open` if ``url`` is a file, or
    ``sqlalchemy.create_engine`` if ``url`` is a SQLAlchemy URL.

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
    - ``ignored``: Ignored filters as ``[(col, vals), ('_sort', cols), ...]``
    - ``excluded``: Excluded columns as ``[col, ...]``
    - ``sort``: Sorted columns as ``[(col, True), ...]``. The second parameter is ``ascending=``
    - ``offset``: Offset as integer. Defaults to 0
    - ``limit``: Limit as integer - ``None`` if limit is not applied
    - ``count``: Total number of rows, if available

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
    })
    controls = _pop_controls(args)

    # Use the appropriate filter function based on the engine
    if engine == 'dataframe':
        data = transform(url) if callable(transform) else url
        return _filter_frame(data, meta=meta, controls=controls, args=args)
    elif engine == 'dir':
        params = {k: v[0] for k, v in args.items() if len(v) > 0 and _path_safe(v[0])}
        url = url.format(**params)
        data = dirstat(url, **args)
        if callable(transform):
            data = transform(data)
        return _filter_frame(data, meta=meta, controls=controls, args=args)
    elif engine == 'file':
        params = {k: v[0] for k, v in args.items() if len(v) > 0 and _path_safe(v[0])}
        url = url.format(**params)
        if not os.path.exists(url):
            raise OSError('url: %s not found' % url)
        # Get the full dataset. Then filter it
        data = gramex.cache.open(url, ext, transform=transform, **kwargs)
        return _filter_frame(data, meta=meta, controls=controls, args=args)
    elif engine == 'sqlalchemy':
        params = {k: v[0] for k, v in args.items() if len(v) > 0 and _sql_safe(v[0])}
        url = url.format(**params)
        engine = sqlalchemy.create_engine(url, **kwargs)
        if query or queryfile:
            if queryfile:
                query = gramex.cache.open(queryfile, 'text')
            query, state = query.format(**params), None
            if isinstance(table, six.string_types):
                state = [table.format(**params)]
            elif isinstance(table, (list, tuple)):
                state = [t.format(**params) for t in table]
            elif table is None:
                state = None
            else:
                raise ValueError('table: must be string or list of strings, not %r' % table)
            all_params = {k: v[0] for k, v in args.items() if len(v) > 0}
            data = gramex.cache.query(text(query), engine, state, params=all_params)
            if callable(transform):
                data = transform(data)
            return _filter_frame(data, meta=meta, controls=controls, args=args)
        elif table:
            table = table.format(**params)
            if callable(transform):
                data = gramex.cache.query(table, engine, [table])
                return _filter_frame(transform(data), meta=meta, controls=controls, args=args)
            else:
                return _filter_db(engine, table, meta=meta, controls=controls, args=args)
        else:
            raise ValueError('No table: or query: specified')
    else:
        raise ValueError('engine: %s invalid. Can be sqlalchemy|file|dataframe' % engine)


def delete(url, meta={}, args=None, engine=None, table=None, ext=None, id=None,
           query=None, queryfile=None, transform=None, **kwargs):
    '''
    Deletes data using URL query parameters. Typical usage::

        count = gramex.data.delete(dataframe, args=handler.args, id=['id'])
        count = gramex.data.delete('file.csv', args=handler.args, id=['id'])
        count = gramex.data.delete('mysql://server/db', table='table', args=handler.args, id='id')

    ``id`` is a column name or a list of column names defining the primary key.
    Calling this in a handler with ``?id=1&id=2`` deletes rows with id is 1 or 2.

    It accepts the same parameters as :py:func:`filter`, and returns the number
    of deleted rows.
    '''
    if engine is None:
        engine = get_engine(url)
    meta.update({'filters': [], 'ignored': []})
    controls = _pop_controls(args)
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
        engine = sqlalchemy.create_engine(url, **kwargs)
        return _filter_db(engine, table, meta=meta, controls=controls, args=args,
                          source='delete', id=id)
    else:
        raise ValueError('engine: %s invalid. Can be sqlalchemy|file|dataframe' % engine)
    return 0


def update(url, meta={}, args=None, engine=None, table=None, ext=None, id=None,
           query=None, queryfile=None, transform=None, **kwargs):
    '''
    Update data using URL query parameters. Typical usage::

        count = gramex.data.update(dataframe, args=handler.args, id=['id'])
        count = gramex.data.update('file.csv', args=handler.args, id=['id'])
        count = gramex.data.update('mysql://server/db', table='table', args=handler.args, id='id')

    ``id`` is a column name or a list of column names defining the primary key.
    Calling this in a handler with ``?id=1&x=2`` updates x=2 where id=1.

    It accepts the same parameters as :py:func:`filter`, and returns the number of updated rows.
    '''
    if engine is None:
        engine = get_engine(url)
    meta.update({'filters': [], 'ignored': []})
    controls = _pop_controls(args)
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
        engine = sqlalchemy.create_engine(url, **kwargs)
        return _filter_db(engine, table, meta=meta, controls=controls, args=args,
                          source='update', id=id)
    else:
        raise ValueError('engine: %s invalid. Can be sqlalchemy|file|dataframe' % engine)
    return 0


def insert(url, meta={}, args=None, engine=None, table=None, ext=None, id=None,
           query=None, queryfile=None, transform=None, **kwargs):
    '''
    Insert data using URL query parameters. Typical usage::

        count = gramex.data.insert(dataframe, args=handler.args, id=['id'])
        count = gramex.data.insert('file.csv', args=handler.args, id=['id'])
        count = gramex.data.insert('mysql://server/db', table='table', args=handler.args, id='id')

    ``id`` is a column name or a list of column names defining the primary key.
    Calling this in a handler with ``?id=3&x=2`` inserts a new record with id=3 and x=2.

    It accepts the same parameters as :py:func:`filter`, and returns the number of updated rows.
    '''
    if engine is None:
        engine = get_engine(url)
    _pop_controls(args)
    meta.update({'filters': [], 'ignored': []})
    # If values do not have equal number of elements, pad them and warn
    rowcount = max(len(val) for val in args.values())
    for key, val in args.items():
        rows = len(val)
        if 0 < rows < rowcount:
            val += [val[-1]] * (rowcount - rows)
            app_log.warning('data.insert: column %s has %d rows not %d. Extended last value %s',
                            key, rows, rowcount, val[-1])
    rows = pd.DataFrame.from_dict(args)
    if engine == 'dataframe':
        rows = _pop_columns(rows, url.columns, meta['ignored'])
        url = url.append(rows)
        return len(rows)
    elif engine == 'file':
        data = gramex.cache.open(url, ext, transform=None, **kwargs)
        rows = _pop_columns(rows, data.columns, meta['ignored'])
        data = data.append(rows)
        gramex.cache.save(data, url, ext, index=False, **kwargs)
        return len(rows)
    elif engine == 'sqlalchemy':
        if table is None:
            raise ValueError('No table: specified')
        engine = sqlalchemy.create_engine(url, **kwargs)
        cols = get_table(engine, table).columns
        rows = _pop_columns(rows, [col.name for col in cols], meta['ignored'])
        if '.' in table:
            kwargs['schema'], table = table.rsplit('.', 1)
        rows.to_sql(table, engine, if_exists='append', index=False, **kwargs)
        return len(rows)
    else:
        raise ValueError('engine: %s invalid. Can be sqlalchemy|file|dataframe' % engine)
    return 0


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
        url = sqlalchemy.engine.url.make_url(url)
    except sqlalchemy.exc.ArgumentError:
        return 'dir' if os.path.isdir(url) else 'file'
    try:
        url.get_driver_name()
        return 'sqlalchemy'
    except sqlalchemy.exc.NoSuchModuleError:
        return url.drivername


def get_table(engine, table):
    '''Return the sqlalchemy table from the engine and table name'''
    if engine not in _METADATA_CACHE:
        _METADATA_CACHE[engine] = sqlalchemy.MetaData()
    metadata = _METADATA_CACHE[engine]
    if '.' in table:
        schema, tbl = table.rsplit('.', 1)
        return sqlalchemy.Table(tbl, metadata, autoload=True, autoload_with=engine, schema=schema)
    else:
        return sqlalchemy.Table(table, metadata, autoload=True, autoload_with=engine)


def _pop_controls(args):
    '''Filter out data controls: sort, limit, offset and column (_c) from args'''
    return {
        key: args.pop(key)
        for key in ('_sort', '_limit', '_offset', '_c')
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


def _filter_col(col, cols):
    if col in cols:
        return col, ''
    # The order of operators is important. ~ is at the end. Otherwise, !~
    # or >~ will also be mapped to ~ as an operator
    for op in ['', '!', '>', '>~', '<', '<~', '!~', '~']:
        if col.endswith(op) and col[:-len(op)] in cols:
            return col[:-len(op)], op
    return None, None


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
    Checks ?c=col&c=-col for filter(). Takes values of ?c= as col_filter and data
    column names as cols. Returns 2 lists: show_cols as columns to show.
    ignored_cols has column names not in the list, i.e. the ?c= parameters that
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
    filters = meta['filters']
    cols_for_update = {}
    for key, vals in args.items():
        if (source in ('update', 'delete') and key in id) or (source == 'select'):
            # Parse column names
            col, op = _filter_col(key, data.columns)
            if col is None:
                meta['ignored'].append((key, vals))
                continue

            # Apply type conversion for values
            conv = data[col].dtype.type
            vals = tuple(conv(val) for val in vals if val)
            if op not in {'', '!'} and len(vals) == 0:
                meta['ignored'].append((key, vals))
                continue

            # Apply filters
            if op == '':
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
            filters.append((col, op, vals))
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
        for key, val in cols_for_update.items():
            original_data.loc[data.index, key] = val
        return data
    else:
        # Apply controls
        if '_sort' in controls:
            meta['sort'], ignore_sorts = _filter_sort_columns(controls['_sort'], data.columns)
            if len(meta['sort']) > 0:
                data = data.sort_values(by=[c[0] for c in meta['sort']],
                                        ascending=[c[1] for c in meta['sort']])
            if len(ignore_sorts) > 0:
                meta['ignored'].append(('_sort', ignore_sorts))
        if '_c' in controls:
            show_cols, hide_cols = _filter_select_columns(controls['_c'], data.columns, meta)
            data = data[show_cols]
            if len(hide_cols) > 0:
                meta['ignored'].append(('_c', hide_cols))
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

    filters = meta['filters']
    if source == 'delete':
        query = sqlalchemy.delete(table)
    elif source == 'update':
        query = sqlalchemy.update(table)
    else:
        query = sqlalchemy.select([table])
    cols_for_update = {}
    for key, vals in args.items():
        # id (combination of cols) - check ONLY when data is updated
        if (source in ('update', 'delete') and key in id) or (source == 'select'):
            # Parse column names
            col, op = _filter_col(key, cols)
            if col is None:
                meta['ignored'].append((key, vals))
                continue

            # Apply type conversion for values
            column = cols[col]
            conv = column.type.python_type
            # In PY2, .python_type returns str. We want unicode
            if conv == six.binary_type:
                conv = six.text_type
            vals = tuple(conv(val) for val in vals)
            if op not in {'', '!'} and len(vals) == 0:
                meta['ignored'].append((key, vals))
                continue

            # Apply filters
            if op == '':
                # Test if column is not NULL. != None is NOT the same as is not None
                query = query.where(column.in_(vals) if len(vals) else column != None)      # noqa
            elif op == '!':
                # Test if column is NULL. == None is NOT the same as is None
                query = query.where(column.notin_(vals) if len(vals) else column == None)   # noqa
            elif op == '>':
                query = query.where(column > min(vals))
            elif op == '>~':
                query = query.where(column >= min(vals))
            elif op == '<':
                query = query.where(column < max(vals))
            elif op == '<~':
                query = query.where(column <= max(vals))
            elif op == '!~':
                query = query.where(column.notlike('%' + '%'.join(vals) + '%'))
            elif op == '~':
                query = query.where(column.like('%' + '%'.join(vals) + '%'))
            filters.append((col, op, vals))
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
        # Apply controls for select
        if '_sort' in controls:
            meta['sort'], ignore_sorts = _filter_sort_columns(controls['_sort'], list(cols.keys()))
            for col, asc in meta['sort']:
                query = query.order_by(cols[col] if asc else cols[col].desc())
            if len(ignore_sorts) > 0:
                meta['ignored'].append(('_sort', ignore_sorts))
        if '_c' in controls:
            show_cols, hide_cols = _filter_select_columns(controls['_c'], list(cols.keys()), meta)
            query = query.with_only_columns([cols[col] for col in show_cols])
            if len(hide_cols) > 0:
                meta['ignored'].append(('_c', hide_cols))
            if len(show_cols) == 0:
                return pd.DataFrame()
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


def download(data, format='json', template=None, **kwargs):
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
    :arg string format: Output format. Can be ``csv|json|html|xlsx|template``
    :arg file template: Path to template file for ``template`` format
    :arg dict kwargs: Additional parameters that are passed to the relevant renderer
    :return: a byte-string with the download file contents

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
        pptgen(target=out, data=data, is_formhandler=True, **kwargs)
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
        if 'data' in spec or 'fromjson' in spec:
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
        kwargs['spec'] = spec
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
    The url can be a .

    It accepts the following parameters:

    :arg str url: path to a directory, or a URL like ``dir:///c:/path/``,
        ``dir:////root/dir/``. Raises ``OSError`` if url points to a missing
        location or is not a directory.
    :arg int timeout: max seconds to wait. ``None`` to wait forever. (default: 10)
    :return: a DataFrame with columns:
        - ``type``: extension with a ``.`` prefix -- or ``dir``
        - ``path``: full path to file / dir
        - ``dir``: directory path to the file
        - ``name``: file name (including extension)
        - ``size``: file size
        - ``mtime``: last modified time

    TODO: max depth, filters, etc
    '''
    try:
        url = sqlalchemy.engine.url.make_url(url)
        target = url.database
    except sqlalchemy.exc.ArgumentError:
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
            result.append({
                'path': path,
                'dir': dirpath,
                'name': name,
                'type': 'dir',
                'size': stat.st_size,
                'mtime': stat.st_mtime,
            })
        for name in filenames:
            path = os.path.join(dirpath, name)
            stat = os.stat(path)
            result.append({
                'path': path,
                'dir': dirpath,
                'name': name,
                'type': os.path.splitext(name)[-1],
                'size': stat.st_size,
                'mtime': stat.st_mtime,
            })
    return pd.DataFrame(result)
