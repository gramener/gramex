---
title: Caching requests
prefix: Cache
...

[TOC]

# Browser caching

The `Cache-Control:` header supersedes previous caching headers (e.g. Expires).
Modern browsers support Cache-Control. This is all we need.

Here is an example of how to use `Cache-Control:`:

```yaml
url:
    pattern: /$YAMLURL/path       # Pick any pattern
    handler: FileHandler          # and handler
    kwargs:
        path: $YAMLPATH/path              # Pass it any arguments
        headers:                          # Define HTTP headers
            Cache-Control: max-age=3600   # Keep page in browser cache for 1 hour (3600 seconds)
```

The cache is used by browsers as well as proxies. You can also specify these
additional options:

- `no-store`: Always check with the server. Always download the response again.
- `no-cache`: Always check with the server, but store result. Download if response has changed.
- `private`: Cache on browsers, not intermediate proxies. The data is sensitive.
- `public`: Cache even if the HTTP status code is an error, or if HTTP authentication is used.

Here are some typical Cache-Control headers. The durations given here are
indicative. Change them based on your needs.

- **External libraries**: cache publicly for 10 years. They never change.
  <br>`Cache-Control: public, max-age=315360000`
- **Static files**: cache publicly for a day. They change rarely.
  <br>`Cache-Control: public, max-age=86400`
- **Shared dashboards**: cache publicly for an hour. Data refreshes slowly.
  <br>`Cache-Control: public, max-age=3600`
- **User dashboards**: cache *privately* for an hour.
  <br>`Cache-Control: private, max-age=3600`

To [reload ignoring the cache](http://stackoverflow.com/a/385491/100904), press
Ctrl-F5 on the browser. Below is a useful reference for `cache-control` checks ([Google Dev Docs](https://developers.google.com/web/fundamentals/performance/optimizing-content-efficiency/images/http-cache-decision-tree.png)):

![HTTP Cache Control](http-cache-decision-tree.png "HTTP Cache Control")

# Server caching

The `url:` handlers accept a `cache:` key that defines caching behaviour. For
example, this configuration at [random](random) generates random letters every
time it is called:

    :::yaml
    random:
        pattern: /$YAMLURL/random
        handler: FunctionHandler
        kwargs:
            function: random.choice(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'])

But adding the `cache:` to this URL caches it the first time it is called. When
[random-cached](random-cached) is reloaded, the same letter is shown every time.

    :::yaml
    random-cached:
        pattern: /$YAMLURL/random-cached
        handler: FunctionHandler
        kwargs:
            function: random.choice(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'])
        cache: true

## Cache keys

The response from any handler is cached against a cache key. By default, this is
the URL. But you can change this using the `cache.key` argument.

For example,
[cache-full-url?x=1](cache-full-url?x=1) and
[cache-full-url?x=2](cache-full-url?x=2) return different values because they
cache the full URL. But
[cache-only-path?x=1](cache-only-path?x=1) and
[cache-only-path?x=2](cache-only-path?x=2) return the same value because they
only cache the path.

    :::yaml
    cache-full-url:
        pattern: /$YAMLURL/cache-full-url
        handler: FunctionHandler
        kwargs:
            function: random.choice(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'])
        cache:
            key: request.uri          # This is the default cache key

    cache-only-path:
        pattern: /$YAMLURL/cache-only-path
        handler: FunctionHandler
        kwargs:
            function: random.choice(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'])
        cache:
            key: request.path     # only use the request path, not arguments

The key can accept multiple values. The values can either be:

- `request.<attr>`: For example, `request.uri` returns the URI request. Valid attributes are:
    - `request.uri`: The default mechanism = `request.path` + `request.uri`
    - `request.path`: Same cache irrespective of query parameters
    - `request.query`:  Same cache irrespective of URL path
    - `request.remote_ip`: Different caches for each client IP address
    - `request.protocol`: Different caches for "http" vs "https"
    - `request.host`: Different caches when serving on multiple domain names
    - `request.method`: Different caches for "GET" vs "POST", etc
- `headers.<header>`: This translates to `handler.request.headers[header]`. For
  example, `headers.Content-Type` returns the `Content-Type` header. The match
  is case-insensitive. Multiple values are joined by comma.
- `args.<arg>`: For example, `args.x` returns the value of the `?x=` query
  parameter. Multiple values are joined by comma.
- `cookies.<cookie>`. This translates to `handler.request.cookies[cookie]`. For
  example, `cookies.user` returns the value of the `user` cookie.
- `user.<attr>`: This translates to `handler.current_user[attr]`. For example,
  `user.email` returns the user's email attribute if it is set.

For example, this configuration caches based on the request URI and user. Each
URI is cached independently for each user ID.

    :::yaml
    cache-by-user-and-browser:
        ...
        cache:
            key:                # Cache based on
              - request.uri     # the URL requested
              - user.id         # and handler.current_user['id'] if it exists

Google, Facebook, Twitter and LDAP provide the `user.id` attribute. DB Auth
provides it if your user table has an `id` column. But you can use any other
attribute instead of `id` -- e.g. `user.email` for Google, `user.screen_name`
for Twitter, etc.


## Cache expiry

You can specify a expiry duration. For example [cache-expiry](cache-expiry)
caches the response for 5 seconds.

    :::yaml
    cache-expiry:
        pattern: /$YAMLURL/cache-expiry
        handler: FunctionHandler
        kwargs:
            function: random.choice(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'])
        cache:
            expiry:
                duration: 5             # Cache the request for 5 seconds

By default, the cache expires either after 10 years, or when the cache store
runs out of space.

## Cache status

By default, only requests that return a HTTP 200 or HTTP 304 status code are cached. You can cache other status codes via the `status:` configuration.

    :::yaml
    url:
      cache-errors:
        pattern: /$YAMLURL/cache-errors
        ...
        cache:
            status: [200, 404, 500]         # Cache all of these HTTP responses

## Cache stores

Gramex provides an in-memory cache, but you can define your own cache in the
root `cache:` section as follows:

```yaml
cache:
    small-in-memory-cache:  # Define a name for the cache
        type: memory        # This is an in-memory cache
        size: 100000        # Just allow 100K of data in the cache

    big-disk-cache:         # Define a name for the cache
        type: disk          # This is an on-disk cache
        path: $YAMLPATH/.cache  # Location of the disk cache directory
        size: 1000000000    # Allow ~1GB of data in the cache
```

Disk caches are based on the
[diskcache](http://www.grantjenks.com/docs/diskcache/) library. When the size
limit is reached, the oldest items are discarded.

By default, Gramex provides a cache called `memory` that has a 500 MB in-memory
cache based on [cachetools](http://pythonhosted.org/cachetools/). When the size
limit is reached, the least recently used items are discarded. This cache is
used by [gramex.cache.open](#data-caching). To change its size, use:

```yaml
cache:
    memory:                 # This is the name of the pre-defined Gramex cache
        type: memory        # This is an in-memory cache
        size: 5000000       # Just allow 5MB of data in the cache instead of 500 MB (default)
```

If you want to use a different cache by default, specify a `default: true`
against the cache. The **last** cache with `default: true` is used as the
default cache.

```yaml
cache:
    memory:
        default: false      # Don't use memory as the default cache
    different-memory-cache:
        type: memory
        size: 1000000000    # Allow ~1GB of data in the cache
        default: true
```

Avoid disk caches when using `default: true`. Disk caches are MUCH slower than
memory caches, and defeats the purpose of data caching.

### Using cache stores

Your functions can access these caches from `cache` object in `gramex.service`.
For example, the default in-memory Gramex cache is at
`gramex.service.cache['memory']`. The disk cache above is at
`gramex.service.cache['big-disk-cache']`.

The cache stores can be treated like a dictionary. They also support a `.set()`
method which accepts an `expire=` parameter. For example:

    :::python
    from gramex import service      # Available only if Gramex is running
    cache = service.cache['big-disk-cache']
    cache['key'] = 'value'
    cache['key']      # returns 'value'
    del cache['key']  # clears the key
    cache.set('key', 'value', expire=30)    # key expires in 30 seconds

## Mixing Python versions

The cache implementation in Python 2 is different from Python 3 because:

- `diskcache`'s sqlite3 versions differ between Python 2 and Python 3
- The cache is stored as a pickle dump in Python 3, and a json dump in Python 2.
  (JSON is faster in Python 2, but slower in Python 3, and does not encode
  bytestrings, besides.)

This means that you cannot have Gramex instances on Python 2 and Python 3 share
the same cache. (Gramex instances running the same Python version can share the
cache.)


## Cache static files

You can cache static files with both server and client side caching. For example,
to cache the `bower_components` and `assets` directories, use this configuration:

    :::yaml
    static_files:
      pattern: /$YAMLURL/(bower_components/.*|assets/.*)    # Map all static files
      handler: FileHandler
      kwargs:
        path: $YAMLPATH/                            # from under this directory
        headers:
          Cache-Control: public, max-age=315360000  # Cache for 10 years on the browser
      cache: true                                   # Also cache on the server

To force a refresh, append `?v=xx` where `xx` is a new number. (The use of `?v=`
is arbitrary. You can use any query parameter instead of `v`.)


# Data caching

`gramex.cache.open` opens files and caches them unless they are changed. You can
use this to load any type of file. For example:

    :::python
    import gramex.cache
    data = gramex.cache.open('data.csv', encoding='utf-8')

This loads `data.csv`  using `pd.read_csv('data.csv', encoding='utf-8')`. The
next time this is called, if `data.csv` in unchanged, the cached results are
returned.

You can also specify that the file is a CSV file by explicitly passing a 2nd
parameter as `'csv'`. For example:

    :::python
    data = gramex.cache.open('data.csv', 'csv', encoding='utf-8')

(**v1.23** made the 2nd parameter optional. It was mandatory before then.)

The 2nd parameter can take the following values:

- `gramex.cache.open(path, 'text', ...)` loads text files using `io.open`. You can use `txt` instead of `text`
- `gramex.cache.open(path, 'json', ...)` loads JSON files using `json.load`
- `gramex.cache.open(path, 'jsondata', ...)` loads JSON files using `pd.read_json`
- `gramex.cache.open(path, 'yaml', ...)` loads YAML files using `yaml.load`
- `gramex.cache.open(path, 'config', ...)` loads YAML files, but also allows variable substitution, imports, and other [config](../config/) files features.
- `gramex.cache.open(path, 'csv', ...)` loads CSV files using `pd.read_csv`
- `gramex.cache.open(path, 'excel', ...)` loads Excel files using `pd.read_excel`. You can use `xlsx` or `xls` instead of `excel`
- `gramex.cache.open(path, 'hdf', ...)` loads HDF files using `pd.read_hdf`
- `gramex.cache.open(path, 'html', ...)` loads HTML files using `pd.read_html`
- `gramex.cache.open(path, 'sas', ...)` loads SAS files using `pd.read_sas`
- `gramex.cache.open(path, 'stata', ...)` loads Stata files using `pd.read_stata`
- `gramex.cache.open(path, 'table', ...)` loads tabular text files using `pd.read_table`
- `gramex.cache.open(path, 'parquet', ...)` loads parquet files using `pd.read_parquet`. Requires [pyarrow](https://pypi.org/project/pyarrow/) or [fastparquet](https://pypi.org/project/fastparquet/)
- `gramex.cache.open(path, 'feather', ...)` loads feather files using `pd.read_feather`. Requires [pyarrow](https://pypi.org/project/pyarrow/)
- `gramex.cache.open(path, 'template', ...)` loads text using `tornado.template.Template`
- `gramex.cache.open(path, 'md', ...)` loads text using `markdown.markdown`. You can use `markdown` instead of `md`

The 2nd parameter can also be a function like `function(path, **kwargs)`. For
example:

    :::python
    # Return file size if it has changed
    file_size = gramex.cache.open('data.csv', lambda path: os.stat(path).st_size)

    # Read Excel file. Keyword arguments are passed to pd.read_excel
    data = gramex.cache.open('data.xlsx', pd.read_excel, sheetname='Sheet1')

To transform the data after loading, you can use a `transform=` function. For
example:

    :::python
    # After loading, return len(data)
    row_count = gramex.cache.open('data.csv', 'csv', transform=len)

    # Return multiple calculations
    def transform(data):
        return {'count': len(data), 'groups': data.groupby('city')}
    result = gramex.cache.open('data.csv', 'csv', transform=transform)

You can also pass a `rel=True` parameter if you want to specify the filename
relative to the current folder. For example, if `D:/app/calc.py` has this code:

    :::python
    conf = gramex.cache.open('config.yaml', 'yaml', rel=True)

... the `config.yaml` will be loaded from the **same directory** as the calling
file, `D:/app/calc.py`, that is from `D:/app/config.yaml`.

To simplify creating callback functions, use `gramex.cache.opener`. This converts
functions that accept a handle or string into functions that accept a filename.
`gramex.cache.opener` opens the file and returns the handle to the function.

For example, to read using [pickle.load][pickle-load], use:

    :::python
    loader = gramex.cache.opener(pickle.load)
    data = gramex.cache.open('template.pickle', loader)

If your function accepts a string instead of a handle, add the `read=True`
parameter. This passes the results of reading the handle instead of the handle.
For example, to compute the [MD5 hash][hashlib] of a file, use:

    :::python
    m = hashlib.md5
    loader = gramex.cache.opener(m.update, read=True)
    data = gramex.cache.open('template.txt', mode='rb', encoding=None, errors=None)

[pickle-load]: https://docs.python.org/2/library/pickle.html#pickle.load
[hashlib]: https://docs.python.org/3/library/hashlib.html


# Query caching

`gramex.cache.query` returns SQL queries as DataFrames and caches the results.
The next time it is called, the query re-runs only if required.

For example, take this slow query:

    :::python
    query = '''
        SELECT sales.date, product.name, SUM(sales.value)
        FROM product, sales
        WHERE product.id = sales.product_id
        GROUP BY (sales.date, product.name)
    '''

If sales data is updated daily, we need not run this query unless the latest
`date` has changed. Then we can use:

    :::python
    data = gramex.cache.query(query, engine, state='SELECT MAX(date) FROM sales')

`gramex.cache.query` is just like [pd.read_sql][read_sql] but with an additional
`state=` parameter. `state` can be a query -- typically a fast running query. If
running the state query returns a different result, the original query is re-run.

`state` can also be a function. For example, if a local file called `.updated` is
changed every time the data is loaded, you can use:

    :::python
    data = gramex.cache.query(query, engine, state=lambda: os.stat('.updated').st_mtime)

[read_sql]: https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_sql.html


# Module caching

The Python `import` statement loads a module only once. If it has been loaded, it
does not reload it.

During development, this means that you need to restart Gramex every time you
change a Python file.

You can reload the module using `six.moves.reload_module(module_name)`, but this
reloads them module every time, even if nothing has changed. If the module has
any large calculations, this slows things down.

Instead, use `gramex.cache.reload_module(module_name)`. This is like
`six.moves.reload_module`, but it reloads *only if the file has changed.*

For example, you can use it in a FunctionHandler:

    :::python
    import my_utils
    import gramex.cache

    def my_function_handler(handler):
        # Code used during development -- reload module if source has changed
        gramex.cache.reload_module(my_utils)
        my_utils.method()

You can use it inside a template:

    {% import my_utils %}
    {% import gramex.cache %}
    {% set gramex.cache.reload_module(my_utils) %}
    (Now my_utils.method() will have the latest saved code)

In both these cases, whenever `my_utils.py` is updated, the latest version will
be used to render the FunctionHandler or template.


# Subprocess streaming

You can run an OS command asynchronously using `gramex.cache.Subprocess`. Use
this instead of [subprocess.Popen][popen] because the latter will block Gramex
until the command runs.

[popen]: https://docs.python.org/3/library/subprocess.html#popen-constructor

Basic usage:

    :::python
    @tornado.gen.coroutine
    def function_handler(handler):
        proc = gramex.cache.Subprocess(['python', '-V'])
        out, err = yield proc.wait_for_exit()
        # out contains stdout result. err contains stderr result
        # proc.proc.returncode contains the return code
        raise tornado.gen.Return('Python version is ' + err.decode('utf-8'))

`out` and `err` contain the stdout and stderr from running `python -V` as bytes.
All keyword arguments supported by `subprocess.Popen` are supported here.

Streaming is supported. This lets you read the contents of stdout and stderr
*while the program runs*. Example:

    :::python
    @tornado.gen.coroutine
    def function_handler(handler):
        proc = gramex.cache.Subprocess(['flake8'],
                                       stream_stdout=[handler.write],
                                       buffer_size='line')
        out, err = yield proc.wait_for_exit()
        # out will be an empty byte string since stream_stdout is specified

This reads the output of `flake8` line by line (since `buffer_size='line'`) and
writes the output by calling `handler.write`. The returned value for `out` is an
empty string.

`stream_stdout` is a list of functions. You can provide any other method here.
For example:

    :::python
    out = []
    proc = gramex.cache.Subprocess(['flake8'],
                                   stream_stdout=[out.append],
                                   buffer_size='line')

... will write the output line-by-line into the `out` list using `out.append`.

`stream_stderr` works the same was as `stream_stdout` but on stderr instead.
