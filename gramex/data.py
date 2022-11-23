'''Query and manipule data from any source.'''
from datetime import datetime
import io
import os
import re
import time
import json
import sqlalchemy as sa
import numpy as np
import pandas as pd
import gramex.cache
from packaging import version
from tornado.escape import json_encode
from typing import Callable, List, Union
from gramex.config import merge, app_log
from gramex.transforms import build_transform
from orderedattrdict import AttrDict
from urllib.parse import urlparse

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
    'stdev': float,  # MS SQL version of stddev
    'stddev': float,
    'rank': int,
    'percent_rank': float,
    # The following types are the same as the columns
    # first, last, min, max, median
}
# List of Python types returned by SQLAlchemy
_numeric_types = {'int', 'long', 'float', 'Decimal'}
# Data processing plugins.
# e.g. plugins['mongodb'] = {'filter': fn, 'insert': fn, ...}
plugins = {}


def filter(
    url: Union[str, pd.DataFrame],
    args: dict = {},
    meta: dict = {},
    engine: str = None,
    ext: str = None,
    columns: dict = None,
    query: str = None,
    queryfile: str = None,
    transform: Callable = None,
    transform_kwargs: dict = {},
    **kwargs: dict,
) -> pd.DataFrame:
    '''Filter data using URL query parameters.

    Examples:
        >>> gramex.data.filter(dataframe, args=handler.args)
        >>> gramex.data.filter('file.csv', args=handler.args)
        >>> gramex.data.filter('mysql://server/db', table='table', args={'user': [user']})

    Parameters:

        url: DataFrame, sqlalchemy URL, directory or file name, http(s) URL
        args: URL query parameters as a dict of lists. Pass handler.args or parse_qs results
        meta: this dict is updated with metadata during the course of filtering
        engine: over-rides the auto-detected engine. Can be 'dataframe', 'file',
            'http', 'https', 'sqlalchemy', 'dir'
        ext: file extension (if url is a file). Defaults to url extension
        columns: database column names to create if required (if url is a database).
            Keys are column names. Values can be SQL types, or dicts with these keys:
                - `type` (str), e.g. `"VARCHAR(10)"`
                - `default` (str/int/float/bool), e.g. `"none@example.org"`
                - `nullable` (bool), e.g. `False`
                - `primary_key` (bool), e.g. `True` -- used only when creating new tables
                - `autoincrement` (bool), e.g. `True` -- used only when creating new tables
        query: optional SQL query to execute (if url is a database),
            `.format`-ed using `args` and supports SQLAlchemy SQL parameters.
            Loads entire result in memory before filtering.
        queryfile: optional SQL query file to execute (if url is a database).
            Same as specifying the `query:` in a file. Overrides `query:`
        transform: optional in-memory transform of source data. Takes
            the result of gramex.cache.open or gramex.cache.query. Must return a
            DataFrame. Applied to both file and SQLAlchemy urls.
        transform_kwargs: optional keyword arguments to be passed to the
            transform function -- apart from data
        **kwargs: Additional parameters are passed to
            [gramex.cache.open][], `sqlalchemy.create_engine` or the plugin's filter

    Returns:
        Filtered DataFrame

    To filter a DataFrame where column x=1 and y=2:

        >>> filtered = gramex.data.filter(dataframe, args={'x': [1], 'y': [2]})

    `args` is always a dict of lists, which is compatible with Gramex's `handler.args`.
    So you can replace the above with:

        >>> filtered = gramex.data.filter(dataframe, args=handle.args)

    To filter ?city=Rome from a CSV/XLS/any file supported by [gramex.cache.open][]:

        >>> gramex.data.filter('path/to/file.csv', rel=True, args={'city': ['Rome']})

    Remaining `kwargs` are passed to [gramex.cache.open][] if `url` is a file. So `rel=True` works

    To filter ?city=Rome from a SQLite, MySQL, PostgreSQL or any SQLAlchemy-supported DB:

        >>> gramex.data.filter('sqlite:///x.db', table='data', args={'city': ['Rome']})

    Remaining `kwargs` are passed to `sqlalchemy.create_engine` if `url` is a SQLAlchemy URL. E.g.

    - `table`: table name (if url is an SQLAlchemy URL), `.format`-ed using `args`.
    - `state`: optional SQL query to check if data has changed.

    TODO: Document how to pass params -- for each database

    If `table` or `query` is passed to an SQLAlchemy url, it is formatted using `args`.
    For example

        >>> data = gramex.data.filter('mysql://server/db', table='{xxx}', args=handler.args)

    ... when passed `?xxx=sales` returns rows from the sales table. Similarly:

        >>> data = gramex.data.filter(
        ...     'mysql://server/db', args=handler.args,
        ...     query='SELECT {col}, COUNT(*) FROM table GROUP BY {col}')

    ... when passsed `?col=City` replaces `{col}` with `City`.

    NOTE: To avoid SQL injection attacks, only keys without spaces are allowed.
    So `?city name=Oslo` **will not** work.

    The URL supports operators filter like this:

    - `?x` selects x is not null
    - `?x!` selects x is null
    - `?x=val` selects x == val
    - `?x!=val` selects x != val
    - `?x>=val` selects x > val
    - `?x>~=val` selects x >= val
    - `?x<=val` selects x < val
    - `?x<~=val` selects x <= val
    - `?x~=val` selects x matches val as a regular expression
    - `?x!~=val` selects x does not match val as a regular expression

    Multiple filters are combined into an AND clause. Ranges can also be
    specified like this:

    - `?x=a&y=b` selects x = a AND y = b
    - `?x>=100&x<=200` selects x > 100 AND x < 200

    If the same column has multiple values, they are combined like this:

    - `?x=a&x=b` selects x IN (a, b)
    - `?x!=a&x!=b` selects x NOT IN (a, b)
    - `?x~=a&x~=b` selects x ~ a|b
    - `?x>=a&x>=b` selects x > MIN(a, b)
    - `?x<=a&x<=b` selects x < MAX(a, b)

    Arguments are converted to the type of the column before comparing. If this
    fails, it raises a ValueError.

    These URL query parameters control the output:

    - `?_sort=col` sorts column col in ascending order. `?_sort=-col` sorts
        in descending order.
    - `?_limit=100` limits the result to 100 rows
    - `?_offset=100` starts showing the result from row 100. Default: 0
    - `?_c=x&_c=y` returns only columns `[x, y]`. `?_c=-col` drops col.

    If a column name matches one of the above, you cannot filter by that column.
    Avoid column names beginning with _.

    To get additional information about the filtering, use:

        meta = {}      # Create a variable which will be filled with more info
        filtered = gramex.data.filter(data, meta=meta, **handler.args)

    The `meta` variable is populated with the following keys:

    - `filters`: Applied filters as `[(col, op, val), ...]`
    - `ignored`: Ignored filters as `[(col, vals), ('_sort', col), ('_by', col), ...]`
    - `excluded`: Excluded columns as `[col, ...]`
    - `sort`: Sorted columns as `[(col, True), ...]`. The second parameter is `ascending=`
    - `offset`: Offset as integer. Defaults to 0
    - `limit`: Limit as integer - `None` if limit is not applied
    - `count`: Total number of rows, if available
    - `by`: Group by columns as `[col, ...]`
    - `inserted`: List of (dict of primary values) for each inserted row

    These variables may be useful to show additional information about the
    filtered data.
    '''
    # Auto-detect engine.
    if engine is None:
        engine = get_engine(url)

    # Pass the meta= argument from kwargs (if any)
    meta.update(
        {
            'filters': [],  # Applied filters as [(col, op, val), ...]
            'ignored': [],  # Ignored filters as [(col, vals), ...]
            'sort': [],  # Sorted columns as [(col, asc), ...]
            'offset': 0,  # Offset as integer
            'limit': None,  # Limit as integer - None if not applied
            'by': [],  # Group by columns as [col, ...]
        }
    )
    args = dict(args)  # Do not modify the args -- keep a copy
    controls = _pop_controls(args)
    transform = _transform_fn(transform, transform_kwargs)
    url, ext, query, queryfile, kwargs = _replace(
        engine, args, url, ext, query, queryfile, **kwargs
    )

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
            raise OSError(f'url: {url} not found')
        # Get the full dataset. Then filter it
        data = gramex.cache.open(url, ext, transform=transform, **kwargs)
        return _filter_frame(data, meta=meta, controls=controls, args=args)
    elif engine.startswith('plugin+'):
        plugin = engine.split('+')[1]
        method = plugins[plugin]['filter']
        return method(
            url=url,
            controls=controls,
            args=args,
            meta=meta,
            query=query,
            columns=columns,
            **kwargs,
        )
    elif engine == 'sqlalchemy':
        table = kwargs.pop('table', None)
        state = kwargs.pop('state', None)
        engine = alter(url, table, columns, **kwargs)
        if query or queryfile:
            if queryfile:
                query = gramex.cache.open(queryfile, 'text')
            if not state:
                if isinstance(table, str):
                    state = table if ' ' in table else [table]
                elif isinstance(table, (list, tuple)):
                    state = list(table)
                elif table is not None:
                    raise ValueError(f'table: must be string or list of strings, not {table!r}')
            all_params = {k: v[0] for k, v in args.items() if len(v) > 0}
            # sa.text() provides backend-neutral :name for bind parameters
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
        raise ValueError(f'engine: {engine} invalid. Can be sqlalchemy|file|dataframe')


def delete(
    url: Union[str, pd.DataFrame],
    meta: dict = {},
    args: dict = {},
    engine: str = None,
    table: str = None,
    ext: str = None,
    id: str = None,
    columns: dict = None,
    query: str = None,
    queryfile: str = None,
    transform: Callable = None,
    transform_kwargs: dict = {},
    **kwargs: dict,
) -> int:
    '''Deletes data using URL query parameters.

    Examples:
        >>> gramex.data.delete(dataframe, args=handler.args, id=['id'])
        >>> gramex.data.delete('file.csv', args=handler.args, id=['id'])
        >>> gramex.data.delete('mysql://server/db', table='x', args=handler.args, id=['id'])

    `id` is a list of column names defining the primary key.
    Calling this in a handler with `?id=1&id=2` deletes rows with id is 1 or 2.

    It accepts the same parameters as [gramex.data.filter][], and returns the number
    of deleted rows.
    '''
    if engine is None:
        engine = get_engine(url)
    meta.update({'filters': [], 'ignored': []})
    args = dict(args)  # Do not modify the args -- keep a copy
    controls = _pop_controls(args)
    url, table, ext, query, queryfile, kwargs = _replace(
        engine, args, url, table, ext, query, queryfile, **kwargs
    )
    if engine == 'dataframe':
        data_filtered = _filter_frame(
            url, meta=meta, controls=controls, args=args, source='delete', id=id
        )
        return len(data_filtered)
    elif engine == 'file':
        data = gramex.cache.open(url, ext, transform=transform, **kwargs)
        data_filtered = _filter_frame(
            data, meta=meta, controls=controls, args=args, source='delete', id=id
        )
        gramex.cache.save(data, url, ext, index=False, **kwargs)
        return len(data_filtered)
    elif engine.startswith('plugin+'):
        plugin = engine.split('+')[1]
        method = plugins[plugin]['delete']
        return method(
            url=url,
            meta=meta,
            controls=controls,
            args=args,
            id=id,
            table=table,
            columns=columns,
            ext=ext,
            query=query,
            queryfile=queryfile,
            **kwargs,
        )
    elif engine == 'sqlalchemy':
        if table is None:
            raise ValueError('No table: specified')
        engine = alter(url, table, columns, **kwargs)
        return _filter_db(
            engine, table, meta=meta, controls=controls, args=args, source='delete', id=id
        )
    else:
        raise ValueError(f'engine: {engine} invalid. Can be sqlalchemy|file|dataframe')


def update(
    url: Union[str, pd.DataFrame],
    meta: dict = {},
    args: dict = {},
    engine: str = None,
    table: str = None,
    ext: str = None,
    id: str = None,
    columns: dict = None,
    query: str = None,
    queryfile: str = None,
    transform: Callable = None,
    transform_kwargs: dict = {},
    **kwargs: dict,
) -> int:
    '''Update data using URL query parameters.

    Examples:
        >>> gramex.data.update(dataframe, args=handler.args, id=['id'])
        >>> gramex.data.update('file.csv', args=handler.args, id=['id'])
        >>> gramex.data.update('mysql://server/db', table='x', args=handler.args, id=['id'])

    `id` is a list of column names defining the primary key.
    Calling this in a handler with `?id=1&x=2` updates x=2 where id=1.

    It accepts the same parameters as [gramex.data.filter][], and returns the number of updated
    rows.
    '''
    if engine is None:
        engine = get_engine(url)
    meta.update({'filters': [], 'ignored': []})
    args = dict(args)  # Do not modify the args -- keep a copy
    controls = _pop_controls(args)
    url, table, ext, query, queryfile, kwargs = _replace(
        engine, args, url, table, ext, query, queryfile, **kwargs
    )
    if engine == 'dataframe':
        data_updated = _filter_frame(
            url, meta=meta, controls=controls, args=args, source='update', id=id
        )
        return len(data_updated)
    elif engine == 'file':
        data = gramex.cache.open(url, ext, transform=transform, **kwargs)
        data_updated = _filter_frame(
            data, meta=meta, controls=controls, args=args, source='update', id=id
        )
        gramex.cache.save(data, url, ext, index=False, **kwargs)
        return len(data_updated)
    elif engine.startswith('plugin+'):
        plugin = engine.split('+')[1]
        method = plugins[plugin]['update']
        return method(
            url=url,
            meta=meta,
            controls=controls,
            args=args,
            id=id,
            table=table,
            columns=columns,
            ext=ext,
            query=query,
            queryfile=queryfile,
            **kwargs,
        )
    elif engine == 'sqlalchemy':
        if table is None:
            raise ValueError('No table: specified')
        engine = alter(url, table, columns, **kwargs)
        return _filter_db(
            engine, table, meta=meta, controls=controls, args=args, source='update', id=id
        )
    else:
        raise ValueError(f'engine: {engine} invalid. Can be sqlalchemy|file|dataframe')


def insert(
    url: Union[str, pd.DataFrame],
    meta: dict = {},
    args: dict = {},
    engine: str = None,
    table: str = None,
    ext: str = None,
    id: str = None,
    columns: dict = None,
    query: str = None,
    queryfile: str = None,
    transform: Callable = None,
    transform_kwargs: dict = {},
    **kwargs: dict,
) -> int:
    '''Insert data using URL query parameters.

    Examples:
        >>> gramex.data.insert(dataframe, args=handler.args, id=['id'])
        >>> gramex.data.insert('file.csv', args=handler.args, id=['id'])
        >>> gramex.data.insert('mysql://server/db', table='x', args=handler.args, id=['id'])

    `id` is a list of column names defining the primary key.
    Calling this in a handler with `?id=3&x=2` inserts a new record with id=3 and x=2.

    If the target file / table does not exist, it is created.

    It accepts the same parameters as [gramex.data.filter][], and returns the number of updated
    rows.
    '''
    if engine is None:
        engine = get_engine(url)
    args = dict(args)  # Do not modify the args -- keep a copy
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
            app_log.warning(
                f'data.insert: column {key} has {rows} rows not {rowcount}. '
                f'Extended last value {val[-1]}'
            )
    rows = pd.DataFrame.from_dict(args)
    url, table, ext, query, queryfile, kwargs = _replace(
        engine, args, url, table, ext, query, queryfile, **kwargs
    )
    if engine == 'dataframe':
        rows = _pop_columns(rows, url.columns, meta['ignored'])
        url = url.append(rows, sort=False)
        return len(rows)
    elif engine == 'file':
        try:
            data = gramex.cache.open(url, ext, transform=None, **kwargs)
        except OSError:
            data = rows
        else:
            rows = _pop_columns(rows, data.columns, meta['ignored'])
            data = data.append(rows, sort=False)
        gramex.cache.save(data, url, ext, index=False, **kwargs)
        return len(rows)
    elif engine.startswith('plugin+'):
        plugin = engine.split('+')[1]
        method = plugins[plugin]['insert']
        return method(url=url, rows=rows, meta=meta, args=args, table=table, **kwargs)
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
        # SQLAlchemy 1.4+ only allows sa.inspect() for all table introspection
        if version.parse(sa.__version__) >= version.parse('1.4'):
            has_table = sa.inspect(engine).has_table(table, schema=kwargs.get('schema'))
        # SQLAlchemy 1.3- does not have .has_table()
        else:
            has_table = engine.dialect.has_table(engine, table, schema=kwargs.get('schema'))
        # If the DB doesn't yet have the table, create it WITH THE PRIMARY KEYS.
        if not has_table and id:
            # Note: pandas does not document get_schema, so it might change.
            engine.execute(pd.io.sql.get_schema(rows, name=table, keys=id, con=engine))

        def insert_method(tbl, conn, keys, data_iter):
            '''Pandas .to_sql() doesn't return inserted row primary keys. Capture it in meta'''
            data = [dict(zip(keys, row)) for row in data_iter]
            # If the ?id= is not provided, Pandas creates a schema based on available columns,
            # without the `id` column. SQLAlchemy won't return inserted_primary_key unless the
            # metadata has a primary key. So, hoping that the table already has a primary key,
            # load table from DB via extend_existing=True.
            sa_table = sa.Table(
                table, tbl.table.metadata, extend_existing=True, autoload_with=engine
            )
            r = conn.execute(sa_table.insert(), data)
            # SQLAlchemy 1.4+ supports inserted_primary_key_rows.
            if hasattr(r, 'inserted_primary_key_rows'):
                ids = r.inserted_primary_key_rows
            # In SQLAlchemy 1.3, only single inserts have an inserted_primary_key.
            elif hasattr(r, 'inserted_primary_key'):
                ids = [r.inserted_primary_key]
            else:
                ids = []
            # Add non-empty IDs as a dict with associated keys.
            # If there are no auto-generated primary keys in the table, no need to return anything.
            id_cols = [col.name for col in sa_table.primary_key]
            for row in ids:
                if row:
                    meta['inserted'].append(dict(zip(id_cols, row)))

        kwargs['method'] = insert_method
        # If user passes ?col= with an empty string, replace with NULL;
        # because, if the column is an INT/FLOAT, type conversion int('') / float('') will fail.
        for col in rows.columns:
            if rows[col].dtype == object:
                rows[col].replace({'': None}, inplace=True)

        # kwargs might contain additonal unexpected values, pass expected arguments explicitly
        pd.io.sql.to_sql(
            rows,
            table,
            engine,
            if_exists='append',
            index=False,
            schema=kwargs.get('schema', None),
            index_label=kwargs.get('index_label', None),
            chunksize=kwargs.get('chunksize', None),
            dtype=kwargs.get('dtype', None),
            method=kwargs.get('method', None),
        )

        return len(rows)
    else:
        raise ValueError(f'engine: {engine} invalid. Can be sqlalchemy|file|dataframe')


def get_engine(url: Union[str, pd.DataFrame]) -> str:
    '''Detect the type of url passed.

    The return value is

    - `'dataframe'` if url is a Pandas DataFrame
    - `'sqlalchemy'` if url is a sqlalchemy compatible URL
    - `'plugin'` if it is `<valid-plugin-name>://...`
    - `protocol` if url is of the form `protocol://...`
    - `'dir'` if it is not a URL but a valid directory
    - `'file'` if it is not a URL but a valid file
    - `None` otherwise
    '''
    if isinstance(url, pd.DataFrame):
        return 'dataframe'
    for plugin_name in plugins:
        if url.startswith(f'{plugin_name}:'):
            return f'plugin+{plugin_name}'
    try:
        url = sa.engine.url.make_url(url)
    except sa.exc.ArgumentError:
        return 'dir' if os.path.isdir(url) else 'file'
    try:
        url.get_driver_name()
        return 'sqlalchemy'
    except sa.exc.NoSuchModuleError:
        return url.drivername


def create_engine(url: str, create: sa.engine.base.Engine = sa.create_engine, **kwargs: dict):
    '''
    Cached version of sqlalchemy.create_engine (or any custom engine).

    Normally, this is not required. But [gramex.data.get_table][] caches the engine
    *and* metadata *and* uses autoload=True. This makes sqlalchemy create a new
    database connection for every engine object, and not dispose it. So we
    re-use the engine objects within this module.
    '''
    if url not in _ENGINE_CACHE:
        _ENGINE_CACHE[url] = create(url, **kwargs)
    return _ENGINE_CACHE[url]


def get_table(engine: sa.engine.base.Engine, table: str, **kwargs: dict) -> sa.Table:
    '''Return the sqlalchemy table from the engine and table name'''
    if engine not in _METADATA_CACHE:
        _METADATA_CACHE[engine] = sa.MetaData(bind=engine)
    metadata = _METADATA_CACHE[engine]
    if '.' in table:
        kwargs['schema'], table = table.rsplit('.', 1)
    return sa.Table(table, metadata, autoload=True, autoload_with=engine, **kwargs)


def download(
    data: Union[pd.DataFrame, List[pd.DataFrame]],
    format: str = 'json',
    template: str = None,
    args: dict = {},
    **kwargs: dict,
) -> bytes:
    '''
    Download a DataFrame or dict of DataFrames in various formats. This is used
    by [gramex.handlers.FormHandler][]. You are **strongly** advised to
    try it before creating your own FunctionHandler.

    Usage as a FunctionHandler:

        def download_as_csv(handler):
            handler.set_header('Content-Type', 'text/csv')
            handler.set_header('Content-Disposition', 'attachment;filename=data.csv')
            return gramex.data.download(dataframe, format='csv')

    It takes the following arguments:

    Parameters:
        data: A DataFrame or a dict of DataFrames
        format: Output format. Can be `csv|json|html|xlsx|template`
        template: Path to template file for `template` format
        args: dictionary of user arguments to subsitute spec
        **kwargs: Additional parameters that are passed to the relevant renderer

    Returns:
        bytes with the download file contents

    When `data` is a DataFrame, this is what different `format=` parameters
    return:

    - `csv` returns a UTF-8-BOM encoded CSV file of the dataframe
    - `xlsx` returns an Excel file with 1 sheet named `data`. kwargs are
        passed to `.to_excel(index=False)`
    - `html` returns a HTML file with a single table. kwargs are passed to
        `.to_html(index=False)`
    - `json` returns a JSON file. kwargs are passed to
        `.to_json(orient='records', force_ascii=True)`.
    - `template` returns a Tornado template rendered file. The template
        receives `data` as `data` and any additional kwargs.
    - `pptx` returns a PPTX generated by pptgen
    - `seaborn` or `sns` returns a Seaborn generated chart
    - `vega` returns JavaScript that renders a Vega chart

    When `data` is a dict of DataFrames, the following additionally happens:

    - `format='csv'` renders all DataFrames one below the other, adding the
        key as heading
    - `format='xlsx'` renders each DataFrame on a sheet whose name is the key
    - `format='html'` renders tables below one another with the key as heading
    - `format='json'` renders as a dict of DataFrame JSONs
    - `format='template'` sends `data` and all `kwargs` as passed to the
        template
    - `format='pptx'` passes `data` as a dict of datasets to pptgen
    - `format='vega'` passes `data` as a dict of datasets to Vega

    When `data` is NEITHER a DataFrame or a dict of DataFrames:

    - `format='json'` renders as JSON if possible
    - `format='template'` renders the template if possible
    - all other formats raise a `ValueError`

    You need to set the MIME types on the handler yourself. Recommended MIME
    types are in gramex.yaml under handler.FormHandler.
    '''
    multiple_datasets = True
    error_no_dataframe = None

    # Check if data is a DataFrame or a dict of DataFrames (multiple_datasets).
    # Ensure that data becomes a dict of DataFrames
    if isinstance(data, dict):
        for key, val in data.items():
            if not isinstance(val, pd.DataFrame):
                error_no_dataframe = f'download(): {key} type is {type(val)}, not a DataFrame'
        if not len(data):
            error_no_dataframe = 'download(): got empty dict. Need a DataFrame'
    elif not isinstance(data, pd.DataFrame):
        error_no_dataframe = f'download(): type is {type(data)}, not a DataFrame'
    else:
        data = {'data': data}
        multiple_datasets = False

    # These formats require a DataFrame or a dict of DataFrames. Other formats (json, template)
    # accept anything.
    if error_no_dataframe and format in {
        'csv',
        'html',
        'xlsx',
        'xls',
        'pptx',
        'ppt',
        'seaborn',
        'sns',
        'vega',
        'vega-lite',
        'vegam',
    }:
        raise ValueError(error_no_dataframe)

    def kw(**conf):
        '''Set provided conf as defaults for kwargs'''
        return merge(kwargs, conf, mode='setdefault')

    if format == 'csv':
        # csv.writer requires BytesIO in PY2 and StringIO in PY3.
        # I can't see an elegant way out of this other than writing code for each.
        out = io.StringIO()
        kw(index=False)
        for index, (key, val) in enumerate(data.items()):
            if index > 0:
                out.write('\n')
            if multiple_datasets:
                out.write(key + '\n')
            val.to_csv(out, **kwargs)
        result = out.getvalue()
        # utf-8-sig encoding returns the result with a UTF-8 BOM. Easier to open in Excel
        return result.encode('utf-8-sig') if result.strip() else result.encode('utf-8')
    elif format == 'template':
        return gramex.cache.open(template, 'template').generate(
            data=data if multiple_datasets else data['data'], **kwargs
        )
    elif format == 'html':
        out = io.StringIO()
        kw(index=False)
        for key, val in data.items():
            if multiple_datasets:
                out.write(f'<h1>{key}</h1>')
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
        from gramex.pptgen import pptgen

        kw()
        out = io.BytesIO()
        pptgen(target=out, data=data, **kwargs)
        return out.getvalue()
    elif format in {'seaborn', 'sns'}:
        kw = AttrDict()
        defaults = {
            'chart': 'barplot',
            'ext': 'png',
            'data': 'data',
            'dpi': 96,
            'width': 640,
            'height': 480,
        }
        for key, default in defaults.items():
            kw[key] = kwargs.pop(key, default)
        import matplotlib

        matplotlib.use('Agg')  # Before importing seaborn, set a headless backend
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
    # If it's none of these formats, default to JSON.
    # If there are no DataFrames, handle arbitrary JSON
    elif error_no_dataframe:
        from gramex.config import CustomJSONEncoder

        kw(cls=CustomJSONEncoder)
        return json.dumps(data, **kwargs)
    # If there ARE DataFrames, render each
    else:
        out = io.BytesIO()
        kwargs = kw(orient='records', force_ascii=True)
        if multiple_datasets:
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


def dirstat(url: str, timeout: int = 10, **kwargs: dict) -> pd.DataFrame:
    '''Return a DataFrame with the list of all files & directories under the url.

    Parameters:
        url: path to a directory, or a URL like `dir:///c:/path/`, `dir:////root/dir/`
        timeout: max seconds to wait. `None` to wait forever

    Raises:
        OSError: if url points to a missing location or is not a directory.

    Returns:
        DataFrame with 1 row per file/directory in the URL

    The result has these columns.

    - `type`: extension with a `.` prefix -- or `dir`
    - `dir`: directory path to the file relative to the URL
    - `name`: file name (including extension)
    - `path`: full path to file or dir. This equals url / dir / name
    - `size`: file size
    - `mtime`: last modified time in seconds since epoch
    - `level`: path depth (i.e. the number of paths in dir)
    '''
    try:
        url = sa.engine.url.make_url(url)
        target = url.database
    except sa.exc.ArgumentError:
        target = url
    if not os.path.isdir(target):
        raise OSError(f'dirstat: {target} is not a directory')
    target = os.path.normpath(target)
    result = []
    start_time = time.time()
    for dirpath, dirnames, filenames in os.walk(target):
        if timeout and time.time() - start_time > timeout:
            app_log.debug(f'dirstat: {url} timeout ({timeout:.1f}s)')
            break
        for name in dirnames:
            path = os.path.join(dirpath, name)
            stat = os.stat(path)
            dirname = dirpath.replace(target, '').replace(os.sep, '/') + '/'
            result.append(
                {
                    'path': path,
                    'dir': dirname,
                    'name': name,
                    'type': 'dir',
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                    'level': dirname.count('/'),
                }
            )
        for name in filenames:
            path = os.path.join(dirpath, name)
            stat = os.stat(path)
            dirname = dirpath.replace(target, '').replace(os.sep, '/') + '/'
            result.append(
                {
                    'path': path,
                    'dir': dirname,
                    'name': name,
                    'type': os.path.splitext(name)[-1],
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                    'level': dirname.count('/'),
                }
            )
    return pd.DataFrame(result)


def filtercols(
    url: Union[str, pd.DataFrame],
    args: dict = {},
    meta: dict = {},
    engine: str = None,
    ext: str = None,
    query: str = None,
    queryfile: str = None,
    transform: Callable = None,
    transform_kwargs: dict = {},
    separator: str = ',',
    in_memory: bool = False,
    **kwargs: dict,
) -> pd.DataFrame:
    '''Filter data and extract unique values of each column using URL query parameters.

    Examples:
        >>> gramex.data.filtercols(dataframe, args=handler.args)
        >>> gramex.data.filtercols('file.csv', args=handler.args)
        >>> gramex.data.filtercols('mysql://server/db', table='table', args=handler.args)

    Parameters:

        url: Pandas DataFrame, sqlalchemy URL, directory or file name,
            `.format`-ed using `args`.
        args: URL query parameters as a dict of lists. Pass handler.args or parse_qs results
        meta: this dict is updated with metadata during the course of filtering
        engine: over-rides the auto-detected engine. Can be 'dataframe', 'file',
            'http', 'https', 'sqlalchemy', 'dir'
        ext: file extension (if url is a file). Defaults to url extension
        query: optional SQL query to execute (if url is a database),
            `.format`-ed using `args` and supports SQLAlchemy SQL parameters.
            Loads entire result in memory before filtering.
        queryfile: optional SQL query file to execute (if url is a database).
            Same as specifying the `query:` in a file. Overrides `query:`
        transform (function): optional in-memory transform of source data. Takes
            the result of gramex.cache.open or gramex.cache.query. Must return a
            DataFrame. Applied to both file and SQLAlchemy urls.
        transform_kwargs: optional keyword arguments to be passed to the
            transform function -- apart from data
        separator: string that separates columns in a hierarchy. Defaults to `,`.
            For example, `?_c=a,b` treats columns `a` and `b` as a tuple / hierarchy and
            filters them *together*.
        in_memory: fetch all unique values and compute filters in-memory. Faster,
            but takes more memory.
        **kwargs: Additional parameters are passed to
            [gramex.cache.open][] or `sqlalchemy.create_engine`

    Returns:
        filtered DataFrame

    Remaining kwargs are passed to [gramex.cache.open][] if `url` is a file, or
    `sqlalchemy.create_engine` if `url` is a SQLAlchemy URL.

    If this is used in a handler as

        >>> filtered = gramex.data.filtercols(dataframe, args=handler.args)

    ... then calling the handler with `?_c=state&_c=district` returns all unique values
    in columns of `dataframe` where columns are state and district.

    Column filter is supported like this:

    - `?_c=y&x` returns df with unique values of y where x is not null
    - `?_c=y&x=val` returns df with unique values of y where x == val
    - `?_c=y&y=val` returns df with unique values of y, ignores filter y == val
    - `?_c=y&x>=val` returns df with unique values of y where x > val
    - `?_c=x&_c=y&x=val` returns df with unique values of x ignoring filter x == val
        and returns unique values of y where x == val

    Arguments are converted to the type of the column before comparing. If this
    fails, it raises a ValueError.

    These URL query parameters control the output:

    - `?_sort=col` sorts column col in ascending order. `?_sort=-col` sorts
        in descending order.
    - `?_limit=100` limits the result to 100 rows
    - `?_offset=100` starts showing the result from row 100. Default: 0
    - `?_c=x&_c=y` returns only columns `[x, y]`. `?_c=-col` drops col.

    If a column name matches one of the above, you cannot filter by that column.
    Avoid column names beginning with _.

    You can handle hierarchies by passing `?_c=Country,City` with a comma. This returns all unique
    *combinations* of `Country` and `City`.

    To get the min/max or a column, use aggregations, e.g. `?_c=age|min&_c=age|max`.
    You can use `?_c=age|range` as a shortcut that returns min and max of a column.

    To get additional information about the filtering, use:

        meta = {}      # Create a variable which will be filled with more info
        filtered = gramex.data.filter(data, meta=meta, **handler.args)

    The `meta` variable is populated with the following keys:

    - `filters`: Applied filters as `[(col, op, val), ...]`
    - `ignored`: Ignored filters as `[(col, vals), ('_sort', cols), ...]`
    - `excluded`: Excluded columns as `[col, ...]`
    - `sort`: Sorted columns as `[(col, True), ...]`. The second parameter is `ascending=`
    - `offset`: Offset as integer. Defaults to 0
    - `limit`: Limit as integer - `100` if limit is not applied
    - `count`: Total number of rows, if available

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
        raise ValueError(f'_limit not integer: {limit!r}')
    if in_memory:
        # Fetch the superset data, i.e. all filter columns
        in_memory_args = {'_c': [], '_by': set()}
        for col in args.get('_c', []):
            name, agg = col.rsplit(_agg_sep, 1) if _agg_sep in col else (col, None)
            for c in name.split(separator):
                in_memory_args['_by'].add(c)
        # Apply all filters while fetching, if skip the filter columns.
        # We'll apply THOSE filters independently
        for key, vals in args.items():
            col = key
            for op in operators:
                if col.endswith(op):
                    col = col[: -len(op)]
                    break
            if _agg_sep in col:
                col = col.rsplit(_agg_sep, 1)[0]
            if col not in in_memory_args['_by']:
                in_memory_args[key] = vals
        url = filter(url, args=in_memory_args, **kwargs)

    # Get unique values for each column
    for col in args.get('_c', []):
        # If ?_c=sales|RANGE, get the range
        name, agg = col.rsplit(_agg_sep, 1) if _agg_sep in col else (col, None)
        # If ?_c=a,b then treat columns a and b as a pair
        cols = name.split(separator)
        # col_args takes _sort, _c and all filters from args
        col_args = {}
        for key, value in args.items():
            # Apply only _sort as a control. Ignore _by, _limit, _offset, etc.
            if key in ['_sort']:
                col_args[key] = value
            # Apply filters. But ignore filters on the columns we're currently processing
            if not key.startswith('_') and key not in cols:
                col_args[key] = value
        if agg:
            # Convert ?_c=col|RANGE to ?_c=col|MIN&_c=col|MAX
            aggs = ['min', 'max'] if agg.lower() == 'range' else [agg]
            # Group by all values, just return the aggregations
            col_args['_by'] = ['']
            col_args['_c'] = [f'{c}{_agg_sep}{a}' for c in cols for a in aggs]
        else:
            col_args['_by'] = cols
            col_args['_c'] = []
            col_args['_limit'] = [limit]
        result[col] = gramex.data.filter(url, args=col_args, **kwargs)
    return result


def alter(url: str, table: str, columns: dict = None, **kwargs: dict) -> sa.engine.base.Engine:
    '''Create or alter a table with columns specified.

    Examples:
        >>> gramex.data.alter(url, table, columns={
        ...     'id': {'type': 'int', 'primary_key': True, 'autoincrement': True},
        ...     'when': {'type': 'timestamp', 'default': {'function': 'func.now()'}},
        ...     'email': {'nullable': True, 'default': 'none'},
        ...     'age': {'type': 'float', 'nullable': False, 'default': 18},
        ... })

    Parameters:
        url: sqlalchemy URL
        table: table name
        columns: column names, with values as SQL types or type objects
        **kwargs: passed to `sqlalchemy.create_engine()`.

    Returns:
        SQLAlchemy engine

    If the table exists, new columns (if any) are added. Existing columns are **NOT changed**.

    If the table does not exist, the table is created with the specified columns.

    `columns` can be a dict with values as SQL types (e.g. `"INTEGER"` or `"VARCHAR(10)"`):

        >>> gramex.data.alter(url, table, columns={'id': 'INTEGER', 'name': 'VARCHAR(10)'})

    ... or a dict like `{column_name: type, column_name: type, ...}`:

        >>> gramex.data.alter(url, table, columns={
        ...     'id': {'type': 'int', 'primary_key': True, 'autoincrement': True},
        ...     'when': {'type': 'timestamp', 'default': {'function': 'func.now()'}},
        ...     'email': {'nullable': True, 'default': 'none'},
        ...     'age': {'type': 'float', 'nullable': False, 'default': 18},
        ... })

    If the `columns` values are a dict, these keys are allowed:

    - `type` (str): SQL type, e.g. `"VARCHAR(10)"`
    - `default` (str/int/float/bool/function/dict):
        - A scalar like `"none@example.org"` for fixed default values
        - A SQLAlchemy function like `sqlalchemy.func.now()`
        - A dict like `{function: func.now()}` containing a SQLAlchemy functions
    - `nullable` (bool): whether column can have null values, e.g. `False`
    - `primary_key` (bool): whether column is a primary key, e.g. `True`
    - `autoincrement` (bool): whether column automatically increments, e.g. `True`

    `primary_key` and `autoincrement` are used **only** when creating new tables. They do not
    change existing primary keys or autoincrements. This is because
    [SQLite disallows PRIMARY KEY with ALTER](https://stackoverflow.com/a/1120030/100904)
    and AUTO_INCREMENT doesn't work without PRIMARY KEY in MySQL.
    '''
    engine = create_engine(url, **kwargs)
    if columns is None:
        return engine
    # alter is not required for schema-less databases. For now, hard-code engine names
    scheme = urlparse(url).scheme
    if scheme in {'mongodb', 'elasticsearch', 'influxdb'}:
        app_log.info(f'alter() not required for schema-less DB {engine.driver}')
        return engine
    try:
        db_table = get_table(engine, table, extend_existing=True)
    except sa.exc.NoSuchTableError:
        # If the table's not in the DB, create it
        cols = []
        for name, row in columns.items():
            row = dict({'type': row} if isinstance(row, str) else row, name=name)
            col_type = row.get('type', 'text')
            if isinstance(col_type, str):
                # Use eval() to handle direct types like INTEGER *and* expressions like VARCHAR(3)
                # eval() is safe here since `col_type` is written by app developer
                # B307:eval is safe here since `col_type` is written by app developer
                row['type'] = eval(col_type.upper(), vars(sa.types))  # nosec B307
            row['type_'] = row.pop('type')
            if 'default' in row:
                from inspect import isclass

                default = row.pop('default')
                # default: can be a string like `'sa.func.now()'` or `'func.now()'`
                if isinstance(default, dict):
                    libs = {'sa': sa, 'sqlalchemy': sa, 'func': sa.func}
                    row['server_default'] = build_transform(
                        default, vars={key: None for key in libs}, iter=False
                    )(**libs)
                # default can be an SQLAlchemy function, e.g. sa.func.now()
                elif isclass(default) and issubclass(default, sa.func.Function):
                    row['server_default'] = default
                # default can also be a static value, e.g. `0`
                else:
                    row['server_default'] = str(default)
            cols.append(sa.Column(**row))
        sa.Table(table, _METADATA_CACHE[engine], *cols, extend_existing=True).create(engine)
    else:
        quote = engine.dialect.identifier_preparer.quote_identifier
        # If the table's already in the DB, add new columns. We can't change column types
        with engine.connect() as conn, conn.begin():
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
                    if isinstance(row['default'], dict) or callable(row['default']):
                        app_log.warning(
                            f'alter(): col {name} cannot change default on existing table'
                        )
                    else:
                        constraints += ['DEFAULT', repr(row['default'])]
                # This syntax works on DB2, MySQL, Oracle, PostgreSQL, SQLite
                conn.execute(
                    f'ALTER TABLE {quote(table)} '
                    f'ADD COLUMN {quote(name)} {col_type} {" ".join(constraints)}'
                )
        # Refresh table metadata after altering
        get_table(engine, table, extend_existing=True)
    return engine


def _transform_fn(transform, transform_kwargs):
    if callable(transform) and transform_kwargs is not None:
        return lambda v: transform(v, **transform_kwargs)
    return transform


def _replace(engine, args, *vars, **kwargs):
    escape = _sql_safe if engine == 'sqlalchemy' else _path_safe
    params = {k: v[0] for k, v in args.items() if len(v) > 0 and escape(v[0])}

    def _format(val):
        if isinstance(val, str):
            return val.format(**params)
        if isinstance(val, list):
            return [_format(v) for v in val]
        if isinstance(val, dict):
            return AttrDict([(k, _format(v)) for k, v in val.items()])
        return val

    return _format(list(vars)) + [_format(kwargs)]


def _pop_controls(args):
    '''Filter out data controls: _sort, _limit, _offset, _c (column) and _by from args'''
    return {
        key: args.pop(key) for key in ('_sort', '_limit', '_offset', '_c', '_by') if key in args
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
    if isinstance(val, str):
        return not re.search(r'\s', val)
    elif isinstance(val, (int, float, bool)):
        return True
    return False


def _path_safe(path):
    '''Returns True if path does not try to escape outside a given directory using .. or / etc'''
    # Ignore non-strings. These are generally not meant for paths
    if not isinstance(path, str):
        return True
    return os.path.realpath(os.path.join(_path_safe_root, path)).startswith(_path_safe_root)


# The order of operators is important. ~ is at the end. Otherwise, !~
# or >~ will also be mapped to ~ as an operator
operators = ['!', '>', '>~', '<', '<~', '!~', '~']


def _filter_col(col, cols):
    '''
    Parses a column name from a list of columns and returns a (col, agg, op)
    tuple.

    - `col` is the name of the column in cols.
    - `agg` is the aggregation operation (SUM, MIN, MAX, etc), else None
    - `op` is the operator ('', !, >, <, etc)

    If the column is invalid, then `col` and `op` are None
    '''
    colset = set(cols)
    # ?col= is returned quickly
    if col in colset:
        return col, None, ''
    # Check if it matches a non-empty operator, like ?col>~=
    for op in operators:
        if col.endswith(op):
            name = col[: -len(op)]
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


def _convertor(conv):
    '''
    Updates a type conversion function.

    Booleans are converted treating '', '0', 'n', 'no', 'f', 'false' (in any case) as False.
    Datetimes are converted using dateutil parser.
    '''
    # Convert based on Pandas datatype. But for boolean, convert from string as below
    if conv in {np.bool_, bool}:
        conv = lambda v: False if v.lower() in {'', '0', 'n', 'no', 'f', 'false'} else True  # noqa
    elif conv in {datetime}:
        from dateutil.parser import parse

        conv = parse
    return conv


def _filter_frame_col(data, key, col, op, vals, meta):
    # Apply type conversion for values
    conv = _convertor(data[col].dtype.type)
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


# If a column has a datetime type, use Pandas to convert strings to datetime values
_sql_types = {datetime: pd.to_datetime}


def _filter_db_col(query, method, key, col, op, vals, column, conv, meta):
    '''
    - Updates `query` with a method (WHERE/HAVING) that sets '<key> <op> <vals>'
    - `column` is the underlying ColumnElement
    - `conv` is a type conversion function that converts `vals` to the correct type
    - Updates `meta` with the fields used for filtering (or ignored)
    '''
    conv = _sql_types.get(conv, conv)
    vals = tuple(conv(val) for val in vals if val)
    if op not in {'', '!'} and len(vals) == 0:
        meta['ignored'].append((key, vals))
    elif op == '':
        # Test if column is not NULL. != None is NOT the same as is not None
        query = method(column.in_(vals) if len(vals) else column != None)  # noqa
    elif op == '!':
        # Test if column is NULL. == None is NOT the same as is None
        query = method(column.notin_(vals) if len(vals) else column == None)  # noqa
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


def _filter_sort_columns(controls: dict, cols: List[str], meta: dict) -> List[str]:
    '''
    Checks ?_sort=col&_sort=-col. Returns list of (columns to sort by, ascending/not).

    Updates meta['sort'] with columns to sort by,
    and meta['ignored'] with unrecognized sort column names as ('_sort', columns)
    '''
    sorts, ignore_sorts = [], []
    if '_sort' in controls:
        for col in controls['_sort']:
            if col in cols:
                sorts.append((col, True))
            elif col.startswith('-') and col[1:] in cols:
                sorts.append((col[1:], False))
            else:
                ignore_sorts.append(col)
        if len(ignore_sorts) > 0:
            meta['ignored'].append(('_sort', ignore_sorts))
        meta['sort'] = sorts
    return sorts


def _filter_select_columns(controls, cols, meta):
    '''
    Checks ?_c=col&_c=-col. Takes values of ?_c= as col_filter and
    data column names as cols. Returns list of columns to show.

    Updates meta['excluded'] with columns explicitly excluded,
    and meta['ignored'] with unrecognized column names.
    '''
    if '_c' not in controls:
        return cols
    selected_cols, excluded_cols, ignored_cols = [], set(), []
    for col in controls['_c']:
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
    if ignored_cols:
        meta['ignored'].append(('_c', ignored_cols))
    return show_cols


def _filter_offset_limit(controls, meta):
    offset, limit = 0, None
    if '_offset' in controls:
        try:
            offset = min(int(v) for v in controls['_offset'])
        except ValueError:
            raise ValueError(f'_offset not integer: {controls["_offset"]!r}')
        meta['offset'] = offset
    if '_limit' in controls:
        try:
            limit = min(int(v) for v in controls['_limit'])
        except ValueError:
            raise ValueError(f'_limit not integer: {controls["_limit"]!r}')
        meta['limit'] = limit
    return offset, limit


def _filter_groupby_columns(by, cols, meta):
    '''
    Checks ?_by=col&_by=col for filter().

    - `by`: list of column names to group by
    - `cols`: list of valid column names
    - `meta`: meta['by'] and meta['ignored'] are updated

    Returns a list of columns to group by
    '''
    colset = set(cols)
    for col in by:
        if col in colset and col not in meta['by']:
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


def _filter_frame(
    data: pd.DataFrame,
    meta: dict,
    controls: dict,
    args: dict,
    source: str = 'select',
    id: List[str] = [],
) -> pd.DataFrame:
    '''
    If `source` is `'select'`, returns a DataFrame in which the DataFrame
    `data` is filtered using `args`. Additional controls like _sort, etc are
    in `controls`. Metadata is stored in `meta`.

    If `source` is `'update'`, filters using `args` but only for columns
    mentioned in `id`. Resulting DataFrame is updated with remaining `args`.
    Returns the updated rows.

    If `source` is `'delete'`, filters using `args` but only for columns
    mentioned in `id`. Deletes these rows. Returns the deleted rows.

    Parameters:
        data: dataframe
        meta: dictionary of `filters`, `ignored`, `sort`, `offset`, `limit` params from kwargs
        args: user arguments to filter the data
        source: accepted values - `update`, `delete` for PUT, DELETE methods in FormHandler
        id: list of id specific to data using which values can be updated
    '''
    original_data = data
    cols_for_update = {}
    cols_having = []
    for key, vals in args.items():
        # check if `key` is in the `id` list -- ONLY when data is updated
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
                col_list = [
                    col + _agg_sep + 'sum'
                    for col in data.columns
                    if pd.api.types.is_numeric_dtype(data[col])
                ]
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
                    data = data.iloc[:, : len(by)]
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
            show_cols = _filter_select_columns(controls, data.columns, meta)
            data = data[show_cols]
        sorts = _filter_sort_columns(controls, data.columns, meta)
        if sorts:
            data = data.sort_values(by=[c[0] for c in sorts], ascending=[c[1] for c in sorts])
        offset, limit = _filter_offset_limit(controls, meta)
        if offset is not None:
            data = data.iloc[offset:]
        if limit is not None:
            data = data.iloc[:limit]
        return data


def _filter_db(
    engine: str,
    table: str,
    meta: dict,
    controls: dict,
    args: dict,
    source: str = 'select',
    id: List[str] = [],
):
    '''
    Parameters:
        engine: constructed sqlalchemy string
        table: table name in the mentioned database
        meta: dictionary of `filters`, `ignored`, `sort`, `offset`, `limit` params from kwargs
        controls: dictionary of `_sort`, `_c`, `_offset`, `_limit` params
        args: dictionary of user arguments to filter the data
        source: accepted values - `update`, `delete` for PUT, DELETE methods in FormHandler
        id: list of keys specific to data using which values can be updated
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
        # check if `key` is in the `id` list -- ONLY when data is updated
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
            query = _filter_db_col(
                query, query.where, key, col, op, vals, cols[col], cols[col].type.python_type, meta
            )
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
                col_list = [
                    col + _agg_sep + 'sum'
                    for col, column in cols.items()
                    if column.type.python_type.__name__ in _numeric_types
                ]
            agg_cols = AttrDict([(col, cols[col]) for col in by])  # {label: ColumnElement}
            typ = {}  # {label: python type}
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
            # SQLAlchemy 1.4+ only accepts positional arguments for .with_only_columns()
            if version.parse(sa.__version__) >= version.parse('1.4'):
                query = query.with_only_columns(*agg_cols.values())
            # SQLAlchemy 1.3- only accepts a list for .with_only_columns()
            else:
                query = query.with_only_columns(agg_cols.values())
            # Apply HAVING operators
            for key, col, op, vals in cols_having:
                query = _filter_db_col(
                    query, query.having, key, col, op, vals, agg_cols[col], typ[col], meta
                )
        elif '_c' in controls:
            show_cols = _filter_select_columns(controls, colslist, meta)
            query = query.with_only_columns([cols[col] for col in show_cols])
            if len(show_cols) == 0:
                return pd.DataFrame()
        sorts = _filter_sort_columns(controls, colslist + query.columns.keys(), meta)
        for col, asc in sorts:
            orderby = sa.asc if asc else sa.desc
            query = query.order_by(orderby(col))
        offset, limit = _filter_offset_limit(controls, meta)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return pd.read_sql(query, engine)


_VEGA_SCRIPT = os.path.join(_FOLDER, 'download.vega.js')


# MongoDB Operations
# ----------------------------------------

_mongodb_op_map = {'<': '$lt', '<~': '$lte', '>': '$gt', '>~': '$gte', '': '$in', '!': '$nin'}


def _mongodb_query(args, table, id=[], **kwargs):
    # Convert a query like x>=3&x>=4&x>=5 into
    # {"$or": [{x: {$gt: 3}}, {x: {$gt: 4}}, {x: $gt: 5}]}
    row = table.find_one()
    if not row:
        return {}
    conditions = []
    for key, vals in args.items():
        if len(id) and key not in id:
            continue
        col_names = list(row)
        col, agg, op = _filter_col(key, col_names)
        if not col:
            continue
        add = lambda v: conditions.append({col: v})  # noqa
        convert = _convertor(type(row[col])) if col in row else lambda v: v
        if op in {'', '!'}:
            add({_mongodb_op_map[op]: [convert(val) for val in vals if val]})
            if any(not val for val in vals):
                add({'$eq' if op == '!' else '$ne': None})
        elif op in {'>', '>~', '<', '<~'}:
            vals = [convert(val) for val in vals if val]
            if op == '>':
                add({_mongodb_op_map[op]: max(vals)})
            elif op == '<':
                add({_mongodb_op_map[op]: min(vals)})
            elif op == '>~':
                add({_mongodb_op_map[op]: max(vals)})
            elif op == '<~':
                add({_mongodb_op_map[op]: min(vals)})
        elif op == '!~':
            add({"$not": {"$regex": '|'.join(vals), "$options": 'i'}})
        elif op == '~':
            add({"$regex": '|'.join(vals), "$options": 'i'})
        elif col and op in _mongodb_op_map:
            add({_mongodb_op_map[op]: convert(val)} for val in vals)
        # TODO: Handle agg
        # TODO: add meta['ignored']
    return {'$and': conditions} if len(conditions) > 1 else conditions[0] if conditions else {}


def _mongodb_collection(url, database, collection, **kwargs):
    import pymongo

    # Support all MongoDB client arguments
    # https://pymongo.readthedocs.io/en/stable/api/pymongo/mongo_client.html
    mongo_kwargs = {
        'host',
        'port',
        'document_class',
        'tz_aware',
        'connect',
        'type_registry',
        # Other optional parameters can be passed as keyword arguments
        'directConnection',
        'maxPoolSize',
        'minPoolSize',
        'maxIdleTimeMS',
        'maxConnecting',
        'socketTimeoutMS',
        'connectTimeoutMS',
        'server_selector',
        'serverSelectionTimeoutMS',
        'waitQueueTimeoutMS',
        'heartbeatFrequencyMS',
        'appname',
        'driver',
        'event_listeners',
        'retryWrites',
        'retryReads',
        'compressors',
        'zlibCompressionLevel',
        'uuidRepresentation',
        'unicode_decode_error_handler',
        'srvServiceName',
        # Write Concern options
        'w',
        'wTimeoutMS',
        'journal',
        'fsync',
        # Read Concern options
        'readConcernLevel',
        # Replica set keyword arguments
        'replicaSet',
        # Read Preference
        'readPreference',
        'readPreferenceTags',
        'maxStalenessSeconds',
        # Authentication
        'username',
        'password',
        'authSource',
        'authMechanism',
        'authMechanismProperties',
        # TLS/SSL configuration
        'tls',
        'tlsInsecure',
        'tlsAllowInvalidCertificates',
        'tlsAllowInvalidHostnames',
        'tlsCAFile',
        'tlsCertificateKeyFile',
        'tlsCRLFile',
        'tlsCertificateKeyFilePassword',
        'tlsDisableOCSPEndpointCheck',
        'ssl',
        # Client side encryption options
        'auto_encryption_opts',
        # Versioned API options
        'server_api',
    }
    create_kwargs = {key: val for key, val in kwargs.items() if key in mongo_kwargs}
    client = create_engine(url, create=pymongo.MongoClient, **create_kwargs)
    db = client[database]
    return db[collection]


def _mongodb_json(obj):
    # Parse val in keys ending with . as JSON ({"key.": val}), but retain other keys
    result = {}
    for key, val in obj.items():
        if key.endswith('.'):
            result[key[:-1]] = json.loads(val)
        else:
            result[key] = val
    return result


def _filter_mongodb(
    url, controls, args, meta, database=None, collection=None, query=None, columns=None, **kwargs
):
    # TODO: Document function and usage
    table = _mongodb_collection(url, database, collection, **kwargs)
    # TODO: If data is missing, identify columns using columns:
    row = table.find_one(query)
    if not row:
        return pd.DataFrame()
    cols = list(row)
    query = dict(query) if query else _mongodb_query(args, table)

    show_cols = _filter_select_columns(controls, cols, meta)
    if show_cols:
        cursor = table.find(query, show_cols)
    else:
        cursor = table.find(query)
    sorts = _filter_sort_columns(controls, cols, meta)
    if sorts:
        cursor = cursor.sort([(key, +1 if val else -1) for key, val in sorts])
    offset, limit = _filter_offset_limit(controls, meta)
    if offset is not None:
        cursor = cursor.skip(offset)
    if limit is not None:
        cursor = cursor.limit(limit)

    data = pd.DataFrame(list(cursor))
    # Convert Object IDs into strings to allow JSON conversion
    if len(data) > 0:
        import bson

        for col, val in data.iloc[0].items():
            if type(val) in {bson.objectid.ObjectId}:
                data[col] = data[col].map(str)

    return data


def _delete_mongodb(
    url, controls, args, meta, database=None, collection=None, query=None, **kwargs
):
    table = _mongodb_collection(url, database, collection, **kwargs)
    query = _mongodb_query(args, table)
    result = table.delete_many(query)
    return result.deleted_count


def _update_mongodb(
    url, controls, args, meta, database=None, collection=None, query=None, id=[], **kwargs
):
    table = _mongodb_collection(url, database, collection, **kwargs)
    query = _mongodb_query(args, table, id=id)
    row = table.find_one(query)
    if not row:
        return 0

    values = {key: val[-1] for key, val in dict(args).items() if key not in id}
    for key in values.keys():
        convert = _convertor(type(row[key])) if key in row else lambda v: v
        values[key] = convert(values[key])

    result = table.update_many(query, {'$set': _mongodb_json(values)})
    return result.modified_count


def _insert_mongodb(url, rows, meta=None, database=None, collection=None, **kwargs):
    table = _mongodb_collection(url, database, collection, **kwargs)
    result = table.insert_many([_mongodb_json(row) for row in rows.to_dict(orient='records')])
    meta['inserted'] = [{'id': str(id) for id in result.inserted_ids}]
    return len(result.inserted_ids)


# InfluxDB Operations
# ----------------------------------------


def _get_influxdb_schema(client, bucket):
    imports = 'import "influxdata/influxdb/schema"\n'
    meas = client.query_api().query(imports + f'schema.measurements(bucket: "{bucket}")')[0]
    tags = client.query_api().query(imports + f'schema.tagKeys(bucket: "{bucket}")')[0]
    tags = [r.get_value() for r in tags.records]
    tags = [r for r in tags if not r.startswith("_")]
    fields = client.query_api().query(imports + f'schema.fieldKeys(bucket: "{bucket}")')[0]
    return {
        "_measurement": [r.get_value() for r in meas.records],
        "_tags": tags,
        "_fields": [r.get_value() for r in fields.records],
    }


_influxdb_op_map = {"<~": "<=", ">~": ">=", "!": "!=", "": "=="}


def _influxdb_offset_limit(controls):
    offset = controls.pop("_offset", ["-30d"])[0]
    limit = controls.pop("_limit", [False])[0]
    offset = f"start: {offset}"
    if isinstance(limit, str) and not limit.isdigit():
        offset += f", stop: {limit}"
        limit = False

    return offset, limit


def _filter_influxdb(url, controls, args, org=None, bucket=None, query=None, **kwargs):
    with _influxdb_client(url, org=org, **kwargs) as db:
        schema = _get_influxdb_schema(db, bucket)
        cols = schema["_fields"] + schema["_tags"] + schema["_measurement"]
        q = db.query_api()
        offset, limit = _influxdb_offset_limit(controls)
        query = f'from(bucket: "{bucket}")|>range({offset})\n'

        filters = []
        wheres = []
        to_drop = []
        for col in controls.pop("_c", []):
            if col.startswith("-"):
                if col[1:] in schema["_fields"]:
                    wheres.append(f'r._field != "{col[1:]}"')
                else:
                    to_drop.append(col[1:])
            elif col in schema["_fields"]:
                col, agg, op = _filter_col(col, cols)
                op = _influxdb_op_map.get(op, op)
                wheres.append(f'r._field {op} "{col}"')
        if len(wheres):
            wheres = " or ".join(wheres)
            filters.append(f"|> filter(fn: (r) => {wheres})")
        for key, vals in args.items():
            col, agg, op = _filter_col(key, cols)
            op = _influxdb_op_map.get(op, op)
            if col in schema["_fields"]:
                where = " or ".join([f'r._field == "{col}" and r._value {op} {v}' for v in vals])
            else:
                where = " or ".join([f'r["{col}"] {op} "{v}"' for v in vals])
            filters.append(f"|> filter(fn: (r) => {where})")
        query += "\n".join(filters)
        if to_drop:
            to_drop = ",".join([f'"{k}"' for k in to_drop])
            query += f"\n|> drop(columns: [{to_drop}])"

        if limit:
            query += f"|> tail(n: {limit})\n"

        app_log.debug("Running InfluxDB query: \n" + query)

        df = q.query_data_frame(query)
    return df.drop(["result", "table"], axis=1, errors="ignore")


def _delete_influxdb(url, controls, args, org=None, bucket=None, **kwargs):
    with _influxdb_client(url, org=org, **kwargs) as db:
        schema = _get_influxdb_schema(db, bucket)
        start = args.pop('_time>', ['0'])[0]
        stop = args.pop('_time<', ['99999999999'])[0]
        measurement = args.pop('_measurement', schema['_measurement'])[0]
        predicate = f'_measurement="{measurement}"'
        tags = [(k, v[0]) for k, v in args.items() if k in schema['_tags']]
        if tags:
            tag_predicate = " OR ".join([f'{k}="{v}"' for k, v in tags])
            predicate += ' AND ' + f'({tag_predicate})'
        db.delete_api().delete(start, stop, predicate, bucket, org)
    # InfluxDB Python client doesn't return anything on DELETE, we return a mock number here.
    return 0


def _influxdb_client(
    url, token, org, debug=None, timeout=60_000, enable_gzip=False, default_tags=None, **kwargs
):
    from influxdb_client import InfluxDBClient

    url = re.sub(r"^influxdb:", "", url)
    return InfluxDBClient(
        url,
        token,
        org=org,
        debug=debug,
        enable_gzip=enable_gzip,
        default_tags=default_tags,
        timeout=timeout,
    )


def _timestamp_df(df, index_col="_time"):
    """Add timestamp index by parsing `index_col` (default to now)."""
    now = datetime.now().astimezone()
    if index_col not in df:
        df[index_col] = [now] * len(df)
    else:
        df[index_col] = pd.to_datetime(df[index_col], errors="coerce").fillna(now)
    return df.set_index(index_col)


def _get_ts_points(df, measurement, tags):
    from influxdb_client import Point

    points = []
    tags = df[tags]
    fields = df.drop(tags, axis=1)
    for (t, field), (_, tag) in zip(fields.astype(float).iterrows(), tags.iterrows()):
        p = Point(measurement).time(t)
        [p.tag(t, tval) for t, tval in tag.to_dict().items()]
        [p.field(f, fval) for f, fval in field.to_dict().items()]
        points.append(p)
    return points


def _insert_influxdb(url, rows, meta, args, bucket, **kwargs):
    measurement = rows.pop("measurement").unique()[0]
    tags = rows.pop("tags").dropna().drop_duplicates().tolist() if "tags" in rows else []
    # Ensure that the index is timestamped
    rows = _timestamp_df(rows)

    # Ensure that all columns except tags are floats
    field_columns = [c for c in rows if c not in tags]
    rows[field_columns] = rows[field_columns].astype(float)
    from influxdb_client.client.write_api import ASYNCHRONOUS, WriteOptions

    with _influxdb_client(url, **kwargs) as db, db.write_api(
        write_options=WriteOptions(ASYNCHRONOUS, batch_size=50000, flush_interval=10000)
    ) as client:
        client.write(
            bucket=bucket,
            org=db.org,
            record=rows,
            data_frame_measurement_name=measurement,
            data_frame_tag_columns=tags,
        )
    meta["inserted"] = [{"id": ix} for ix, _ in rows.iterrows()]
    return len(rows)


# ServiceNow Operations
# ----------------------------------------


def _filter_servicenow(url, controls, args, meta, table=None, columns=None, query=None, **kwargs):
    import pysnow
    from gramex.config import locate

    urlinfo = urlparse(url)
    c = pysnow.Client(instance=urlinfo.hostname, user=urlinfo.username, password=urlinfo.password)

    config = gramex.cache.open('servicenow.yaml', 'config', rel=True)
    if table is None:
        table = c.resource(api_path=urlinfo.path)

    # Identify column types. Take the default ServiceNow column types. Override based on user
    table_columns = json.loads(json.dumps(config.columns[urlinfo.path]))
    for col, colinfo in (columns or {}).items():
        table_columns.setdefault(col, {}).update(
            colinfo if isinstance(colinfo, dict) else {'type': colinfo}
        )
    for colinfo in table_columns.values():
        colinfo['_convert'] = _convertor(locate(colinfo['type'], modules=['datetime']))
    col_names = table_columns.keys()

    fields = []
    if not query:
        offset, limit = _filter_offset_limit(controls, meta)
        query = pysnow.QueryBuilder()
        query_initiated = False

        for key, value in args.items():
            col, agg, op = _filter_col(key, col_names)
            value = [table_columns[col]['_convert'](val) for val in value]
            if query_initiated:
                query.AND()
            query_initiated = True
            if op == '':
                query.field(col).equals(value)
            elif op == '!':
                query.field(col).not_equals(value)
            elif op == '>':
                query.field(col).greater_than(min(value))
            elif op == '>~':
                query.field(col).greater_than_or_equal(min(value))
            elif op == '<':
                query.field(col).less_than(max(value))
            elif op == '<~':
                query.field(col).less_than_or_equal(max(value))
            elif op == '!~':
                query.field(col).not_contains(value[0])
            elif op == '~':
                query.field(col).contains(value[0])
            else:
                raise ValueError(f'Unknown ServiceNow operator: {op}')

    offset, limit = _filter_offset_limit(controls, meta)
    sorts = _filter_sort_columns(controls, col_names, meta)
    for col, asc in sorts:
        if query_initiated:
            query.AND()
        query_initiated = True
        if asc:
            query.field(col).order_ascending()
        else:
            query.field(col).order_descending()
    fields.extend(_filter_select_columns(controls, col_names, meta))

    if not len(query._query):
        query = {}

    response = table.get(query=query, limit=limit, offset=offset, fields=fields)
    return pd.DataFrame(response.all())


# add test case for inserting nested value ?parent.={child:value}
#   curl --globoff -I -X POST 'http://127.0.0.1:9988/?x.={"2":3}&y.={"true":true}&Name=abcd'
# add test case for updating nested value ?parent.child.={key:value}
#   curl --globoff -I -X PUT 'http://127.0.0.1:9988/?x.2=4&y.true.=[2,3]&Name=abcd'
# add test case for nested document query ?parent.child=value
plugins["mongodb"] = {
    "filter": _filter_mongodb,
    "delete": _delete_mongodb,
    "insert": _insert_mongodb,
    "update": _update_mongodb,
}
plugins["influxdb"] = {
    "filter": _filter_influxdb,
    "delete": _delete_influxdb,
    "insert": _insert_influxdb,
    "update": _insert_influxdb,
}
plugins["servicenow"] = {"filter": _filter_servicenow}
