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

By default, Gramex defines a cache called `memory` that has a 20MB LRU in-memory
cache based on [cachetools](http://pythonhosted.org/cachetools/). Disk caches
are based on the [diskcache](http://www.grantjenks.com/docs/diskcache/) library.
