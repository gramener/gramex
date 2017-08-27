'''
Interact with data from the browser
'''
from __future__ import unicode_literals

import io
import os
import six
import sqlalchemy
import pandas as pd
import gramex.cache
from tornado.escape import json_encode
from gramex.config import merge

_METADATA_CACHE = {}


def filter(url, args={}, meta={}, engine=None, table=None, ext=None,
           query=None, transform=None, **kwargs):
    '''
    Filters data using URL query parameters. Typical usage::

        filtered = gramex.data.filter(dataframe, args=handler.args)
        filtered = gramex.data.filter('file.csv', args=handler.args)
        filtered = gramex.data.filter('mysql://server/db', table='table', args=handler.args)

    It accepts the following parameters:

    :arg source url: Pandas DataFrame, sqlalchemy URL or file name
    :arg dict args: URL query parameters as a dict of lists. Pass handler.args or parse_qs results
    :arg dict meta: this dict is updated with metadata during the course of filtering
    :arg string table: table name (if url is an SQLAlchemy URL)
    :arg string ext: file extension (if url is a file). Defaults to url extension
    :arg string query: optional SQL query to execute (if url is a database).
        Loads entire query result in memory before filtering
    :arg function transform: optional in-memory transform. Takes a DataFrame and
        returns a DataFrame. Applied to both file and SQLAlchemy urls.
    :arg dict kwargs: Additional parameters are passed to
        :py:func:`gramex.cache.open` or ``sqlalchemy.create_engine``
    :return: a filtered DataFrame

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
        data = transform(url) if callable(transform) else url
        return _filter_frame(data, meta=meta, controls=controls, args=args)
    elif engine == 'file':
        if not os.path.exists(url):
            raise OSError('url: %s not found' % url)
        if ext is None:
            ext = os.path.splitext(url)[-1][1:]
        # Only allow methods used by gramex.cache.open that return a DataFrame
        if ext not in {'csv', 'xls', 'xlsx', 'hdf', 'sas', 'stata', 'table'}:
            raise ValueError('ext: %s invalid. Can be csv|xls|xlsx|...' % ext)
        # Get the full dataset. Then filter it
        data = gramex.cache.open(url, ext, transform=transform, **kwargs)
        return _filter_frame(data, meta=meta, controls=controls, args=args)
    elif engine == 'sqlalchemy':
        if table is None:
            raise ValueError('No table: specified')
        engine = sqlalchemy.create_engine(url, **kwargs)
        # If transform= is passed, read the full dataset to apply the transform.
        if callable(transform) or query:
            data = gramex.cache.query(query if query else table, engine, [table])
            if callable(transform):
                data = transform(data)
            return _filter_frame(data, meta=meta, controls=controls, args=args)
        # If no transform= is passed, run the query on the database
        else:
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


def _filter_sort_columns(sort_filter, cols):
    sorts, ignored_sorts = [], []
    for col in sort_filter:
        if col in cols:
            sorts.append((col, True))
        elif col.startswith('-') and col[1:] in cols:
            sorts.append((col[1:], False))
        else:
            ignored_sorts.append(col)
    return sorts, ignored_sorts


def _filter_select_columns(col_filter, cols):
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
    return show_cols, ignored_cols


def _filter_frame(data, meta, controls, args):
    '''
    Returns a DataFrame in which the source DataFrame ``data`` is filtered using
    args. Additional controls like _sort, etc are in ``controls``. Metadata is
    stored in ``meta``.
    '''
    filters = meta['filters']
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
        meta['sort'], ignored_sorts = _filter_sort_columns(controls['_sort'], data.columns)
        if len(meta['sort']) > 0:
            data = data.sort_values(by=[c[0] for c in meta['sort']],
                                    ascending=[c[1] for c in meta['sort']])
        if len(ignored_sorts) > 0:
            meta['ignored'].append(('_sort', ignored_sorts))
    if '_c' in controls:
        show_cols, ignored_cols = _filter_select_columns(controls['_c'], data.columns)
        data = data[show_cols]
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

    filters = meta['filters']
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
        meta['sort'], ignored_sorts = _filter_sort_columns(controls['_sort'], list(cols.keys()))
        for col, asc in meta['sort']:
            query = query.order_by(cols[col] if asc else cols[col].desc())
        if len(ignored_sorts) > 0:
            meta['ignored'].append(('_sort', ignored_sorts))
    if '_c' in controls:
        show_cols, ignored_cols = _filter_select_columns(controls['_c'], list(cols.keys()))
        query = query.with_only_columns([cols[col] for col in show_cols])
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

    When ``data`` is a DataFrame, this is what different ``format=`` parameters return:

    - ``csv`` returns a UTF-8-BOM encoded CSV file of the dataframe
    - ``xlsx`` returns an Excel file with 1 sheet named ``data``.
      kwargs are passed to ``.to_excel(index=False)``
    - ``html`` returns a HTML file with a single table. kwargs are
      passed to ``.to_html(index=False)``
    - ``json`` returns a JSON file. kwargs are passed to
      ``.to_json(orient='records', force_ascii=True)``.
    - ``template`` returns a Tornado template rendered file. The
      template receives ``data`` as ``data`` and any additional kwargs.

    When ``data`` is a dict of DataFrames, the following additionally happens:

    - ``format='csv'`` renders all DataFrames one below the other, adding the key
      as heading
    - ``format='xlsx'`` renders each DataFrame on a sheet whose name is the key
    - ``format='html'`` renders tables below one aother with the key as heading
    - ``format='json'`` renders as a dict of DataFrame JSONs
    - ``format='template'`` receives ``data`` and all ``kwargs`` as passed.

    You need to set the MIME types on the handler yourself. The recommended MIME types are::

        html:   Content-Type: text/html; charset=UTF-8
        xlsx:   Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
                Content-Disposition: attachment;filename=data.xlsx
        json:   Content-Type: application/json
        csv:    Content-Type: text/csv
                Content-Disposition: attachment;filename=data.csv
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
        # TODO: Create and use a FrameWriter
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            for key, val in data.items():
                val.to_excel(writer, sheet_name=key, **kwargs)
        return out.getvalue()
    else:
        out = io.BytesIO()
        kw(orient='records', force_ascii=True)
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
