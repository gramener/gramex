# Caching requests

The `url:` handlers accept a `cache:` key that defines caching behaviour. For
example, this configuration at [random](random) generates random letters every
time it is called:

    random:
        pattern: /$YAMLURL/random
        handler: FunctionHandler
        kwargs:
            function: random.choice
            args: [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']]

But adding the `cache:` to this URL caches it the first time it is called. When
[random-cached](random-cached) is reloaded, the same letter is shown every time.

    random-cached:
        pattern: /$YAMLURL/random-cached
        handler: FunctionHandler
        kwargs:
            function: random.choice
            args: [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']]
        cache: true

**Note**: Currently, only responses that return a HTTP 200 are cached. Any other
response is not cached.

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
- `headers.<header>`: For example, `headers.Content-Type` returns the
  `Content-Type` header. The match is case-insensitive. Multiple values are
  joined by comma.
- `args.<arg>`: For example, `args.x` returns the value of the `?x=` query
  parameter. Multiple values are joined by comma.
- `cookies.<cookie>`. For example, `cookies.user` returns the value of the
  `user` cookie.

For example, this configuration caches based on the request, browser and user, ensuring that the user 

    cache-by-user-and-browser:
        ...
        cache:
            key:                        # Cache based on
              - request.uri             # the URL requested
              - headers.user-agent      # the browser
              - cookies.user            # and the user token


## Cache expiry

You can specify a expiry duration. For example [cache-expiry](cache-expiry)
caches the response for 5 seconds.

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

## Cache stores

Gramex provides an in-memory cache, but you can define your own cache in the
root `cache:` section as follows:

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

Your functions can access these caches at `gramex.services.info.cache[<key>]`.
For example, the default in-memory Gramex cache is at
`gramex.services.info.cache.memory`. The disk cache above is at
`gramex.services.info.cache['big-disk-cache']`.

The cache stores can be treated like a dictionary. They also support a `.set()`
method which accepts an `expire=` parameter. For example:

    cache = gramex.services.info.cache['big-disk-cache']
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
