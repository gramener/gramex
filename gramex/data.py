'''
Interact with data from the browser
'''
import os
import six
import sqlalchemy
import pandas as pd
import gramex.cache


_METADATA_CACHE = {}


def filter(url, args={}, meta={}, engine=None, table=None, ext=None, **kwargs):
    '''
    Filters data using URL query parameters. Typical usage::

        filtered = gramex.data.filter(dataframe, args=handler.args)
        filtered = gramex.data.filter('file.csv', args=handler.args)
        filtered = gramex.data.filter('mysql://server/db', table='table', args=handler.args)

    It accepts the following parameters:

    :arg source url: Pandas DataFrame, sqlalchemy URL or file name
    :arg dict args: URL query parameters as a dict of lists. Pass handler.args or parse_qs results
    :arg dict meta: this dict is updated with metadata during the course of filtering
    :arg string table: table name (when url is an SQLAlchemy URL)
    :arg string ext: file extension (when url is a file). This defaults to the extension of the url

    Remaining kwargs are passed to :py:func:`gramex.cache.open` if ``url`` is a file, or
    ``sqlalchemy.create_engine`` if ``url`` is a SQLAlchemy URL.

    If this is used in a handler as::

        filtered = gramex.data.filter(dataframe, args=handler.args)

    ... then calling the handler with ``?x=1&y=2`` returns all rows in
    ``dataframe`` where x is 1 and y is 2.

    The URL supports operators like this:

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

    - ``?_sort=col`` sorts column col in ascending order. ?_sort=-col sorts in descending order.
    - ``?_limit=100`` limits the result to 100 rows
    - ``?_offset=100`` starts showing the result from row 100. Default: 0
    - ``?_c=x&_c=y`` returns only columns [x, y]

    If a column name matches one of the above, you cannot filter by that column.
    Avoid column names beginning with _.

    To get additional information about the filtering, use::

        meta = {}      # Create a variable which will be filled with more info
        filtered = gramex.data.filter(data, meta=meta, **handler.args)

    The ``meta`` variable is populated with the following keys:

    - ``filters``: Applied filters as ``[(col, op, val), ...]``
    - ``ignored``: Ignored filters as ``[(col, vals), ('_sort', vals), ...]``
    - ``sort``: Sorted columns as ``[(col, True), ...]``. The second parameter is ``ascending=``
    - ``offset``: Offset as integer. Defaults to 0
    - ``limit``: Limit as integer - ``None`` if limit is not applied

    These variables may be useful to show additional information about the
    filtered data.
    '''
    # Auto-detect engine.
    # If it's a DataFrame, use frame
    # If it's a sqlalchemy parseable URL, use sqlalchemy
    # Else, use 'file'
    if engine is None:
        if isinstance(url, pd.DataFrame):
            engine = 'dataframe'
        else:
            try:
                sqlalchemy.engine.url.make_url(url)
                engine = 'sqlalchemy'
            except sqlalchemy.exc.ArgumentError:
                engine = 'file'

    # Pass the meta= argument from kwargs (if any)
    meta.update({
        'filters': [],      # Applied filters as [(col, op, val), ...]
        'ignored': [],      # Ignored filters as [(col, vals), ...]
        'sort': [],         # Sorted columns as [(col, asc), ...]
        'offset': 0,        # Offset as integer
        'limit': None,      # Limit as integer - None if not applied
    })
    # Filter out controls like sort, limit, etc from args
    controls = {
        key: args.pop(key)
        for key in ('_sort', '_limit', '_offset', '_c')
        if key in args
    }

    # Use the appropriate filter function based on the engine
    if engine == 'dataframe':
        return _filter_frame(url, meta=meta, controls=controls, args=args)
    elif engine == 'file':
        if not os.path.exists(url):
            raise OSError('url: %s not found' % url)
        if ext is None:
            ext = os.path.splitext(url)[-1][1:]
        # Only allow methods used by gramex.cache.open that return a DataFrame
        if ext not in {'csv', 'xls', 'xlsx', 'hdf', 'sas', 'stata', 'table'}:
            raise ValueError('ext: %s invalid. Can be csv|xls|xlsx|...' % ext)
        # Get the full dataset. Then filter it
        data = gramex.cache.open(url, ext, **kwargs)
        return _filter_frame(data, meta=meta, controls=controls, args=args)
    elif engine == 'sqlalchemy':
        if table is None:
            raise ValueError('No table: specified')
        engine = sqlalchemy.create_engine(url, **kwargs)
        return _filter_db(engine, table, meta=meta, controls=controls, args=args)
    else:
        raise ValueError('engine: %s invalid. Can be sqlalchemy|file|dataframe' % engine)


def _filter_col(col, cols):
    if col in cols:
        return col, ''
    # The order of operators is important. ~ is at the end. Otherwise, !~
    # or >~ will also be mapped to ~ as an operator
    for op in ['', '!', '>', '>~', '<', '<~', '!~', '~']:
        if col.endswith(op) and col[:-len(op)] in cols:
            return col[:-len(op)], op
    return None, None


def _filter_frame(data, meta, controls, args):
    '''
    Returns a DataFrame in which the source DataFrame ``data`` is filtered using
    args. Additional controls like _sort, etc are in ``controls``. Metadata is
    stored in ``meta``.
    '''
    filters, sorts = meta['filters'], meta['sort']
    for key, vals in args.items():
        # Parse column names
        col, op = _filter_col(key, data.columns)
        if col is None:
            meta['ignored'].append((key, vals))
            continue

        # Apply type conversion for values
        conv = data[col].dtype.type
        vals = tuple(conv(val) for val in vals)

        # Apply filters
        if op == '':
            data = data[data[col].isin(vals)]
        elif op == '!':
            data = data[~data[col].isin(vals)]
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
    # Apply controls
    if '_sort' in controls:
        ignored_sorts = []
        for col in controls['_sort']:
            if col in data.columns:
                sorts.append((col, True))
            elif col.startswith('-') and col[1:] in data.columns:
                sorts.append((col[1:], False))
            else:
                ignored_sorts.append(col)
        if len(sorts) > 0:
            data = data.sort_values([c[0] for c in sorts], ascending=[c[1] for c in sorts])
        if len(ignored_sorts) > 0:
            meta['ignored'].append(('_sort', ignored_sorts))
    if '_c' in controls:
        ignored_cols = []
        for col in controls['_c']:
            if col not in data.columns:
                ignored_cols.append(col)
        data = data[[col for col in controls['_c'] if col in data.columns]]
        if len(ignored_cols) > 0:
            meta['ignored'].append(('_c', ignored_cols))
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


def _filter_db(engine, table, meta, controls, args):
    if engine not in _METADATA_CACHE:
        _METADATA_CACHE[engine] = sqlalchemy.MetaData()
    metadata = _METADATA_CACHE[engine]
    table = sqlalchemy.Table(table, metadata, autoload=True, autoload_with=engine)
    cols = table.columns

    filters, sorts = meta['filters'], meta['sort']
    query = sqlalchemy.select([table])
    for key, vals in args.items():
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

        # Apply filters
        if op == '':
            query = query.where(column.in_(vals))
        elif op == '!':
            query = query.where(column.notin_(vals))
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
    # Apply controls
    if '_sort' in controls:
        ignored_sorts = []
        for col in controls['_sort']:
            if col in cols:
                sorts.append((col, True))
                query = query.order_by(cols[col])
            elif col.startswith('-') and col[1:] in cols:
                sorts.append((col[1:], False))
                query = query.order_by(cols[col[1:]].desc())
            else:
                ignored_sorts.append(col)
        if len(ignored_sorts) > 0:
            meta['ignored'].append(('_sort', ignored_sorts))
    if '_c' in controls:
        ignored_cols = []
        for col in controls['_c']:
            if col not in cols:
                ignored_cols.append(col)
        show_cols = [cols[col] for col in controls['_c'] if col in cols]
        query = query.with_only_columns(show_cols)
        if len(ignored_cols) > 0:
            meta['ignored'].append(('_c', ignored_cols))
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
