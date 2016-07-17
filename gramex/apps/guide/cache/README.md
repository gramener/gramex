title: Caching requests

Responses can be cached on the browser or the server. This section explains how
both work.

# Browser caching

The `Cache-Control:` header supersedes previous caching headers (e.g. Expires).
Modern browsers support Cache-Control. This is all we need.

Here is an example of how to use `Cache-Control:`:

    url:
        pattern: /$YAMLURL/path       # Pick any pattern
        handler: FileHandler          # and handler
        kwargs:
          path: $YAMLPATH/path        # Pass it any arguments
          headers:                    # Define HTTP headers
            Cache-Control: max-age=3600   # Keep page in browser cache for 1 hour (3600 seconds)

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
Ctrl-F5 on the browser.


# Server caching

The `url:` handlers accept a `cache:` key that defines caching behaviour. For
example, this configuration at [random](random) generates random letters every
time it is called:

    :::yaml
    random:
        pattern: /$YAMLURL/random
        handler: FunctionHandler
        kwargs:
            function: random.choice
            args: [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']]

But adding the `cache:` to this URL caches it the first time it is called. When
[random-cached](random-cached) is reloaded, the same letter is shown every time.

    :::yaml
    random-cached:
        pattern: /$YAMLURL/random-cached
        handler: FunctionHandler
        kwargs:
            function: random.choice
            args: [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']]
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
            function: random.choice
            args: [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']]
        cache:
            key: request.uri          # This is the default cache key

    cache-only-path:
        pattern: /$YAMLURL/cache-only-path
        handler: FunctionHandler
        kwargs:
            function: random.choice
            args: [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']]
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
              - user.id         # and handler.current_user['email'] if it exists

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
            function: random.choice
            args: [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']]
        cache:
            expiry:
                duration: 5             # Cache the request for 5 seconds

By default, the cache expires either after 10 years, or when the cache store
runs out of space.

## Cache status

By default, only requests that return a HTTP 200 status code are cached. You can
cache other status codes via the `status:` configuration.

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

    :::yaml
    cache:
        small-in-memory-cache:  # Define a name for the cache
            type: memory        # This is an in-memory cache
            size: 100000        # Just allow 100K of data in the cache

        big-disk-cache:         # Define a name for the cache
            type: disk          # This is an on-disk cache
            path: $YAMLPATH/.cache  # Location of the disk cache directory
            size: 1000000000    # Allow ~1GB of data in the cache

By default, Gramex provides a cache called `memory` that has a 20MB in-memory
cache based on [cachetools](http://pythonhosted.org/cachetools/). When the size
limit is reached, the least recently used items are discarded.

Disk caches are based on the
[diskcache](http://www.grantjenks.com/docs/diskcache/) library. When the size
limit is reached, the oldest items are discarded.

### Using cache stores

Your functions can access these caches at `gramex.service.cache[<key>]`.
For example, the default in-memory Gramex cache is at
`gramex.service.cache.memory`. The disk cache above is at
`gramex.service.cache['big-disk-cache']`.

The cache stores can be treated like a dictionary. They also support a `.set()`
method which accepts an `expire=` parameter. For example:

    :::python
    cache = gramex.service.cache['big-disk-cache']
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

You can cache static files with both server and client side caching. For
example, to cache the `bower_components` directory, use this configuration:

    :::yaml
    bower_components:
      pattern: /$YAMLURL/bower_components/(.*)      # Map everything under bower_components
      handler: FileHandler                          # via a FileHandler
      kwargs:
        path: $YAMLPATH/bower_components/           # to the bower_components/ directory
        headers:
          Cache-Control: public, max-age=315360000  # Cache for 10 years on the browser
      cache: true                                   # Also cache on the server

To force a refresh, append `?v=xx` where `xx` is a new number. (The use of `?v=`
is arbitrary. You can use any query parameter instead of `v`.)
