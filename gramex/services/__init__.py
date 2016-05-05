'''
This module is a service registry for ``gramex.yaml``. Each key must have a
corresponding function in this file.

For example, if ``gramex.yaml`` contains this section::

    log:
        version: 1


... then :func:`log` is called as ``log({"version": 1})``. If no such function
exists, a warning is raised.
'''

import yaml
import string
import logging
import posixpath
import mimetypes
import webbrowser
import tornado.web
import tornado.ioloop
import logging.config
import six.moves.urllib.parse as urlparse
from orderedattrdict import AttrDict
from . import scheduler
from . import watcher
from . import urlcache
from ..config import locate


# Service-specific information
info = AttrDict(
    app=None,
    schedule=AttrDict(),
    cache=AttrDict(),
)


def version(conf):
    "Check if config version is supported. Currently, only 1.0 is supported"
    if conf != 1.0:
        raise NotImplementedError('version: %s is not supported. Only 1.0', conf)


def log(conf):
    "Set up logging using Python's standard logging.config.dictConfig()"
    logging.config.dictConfig(conf)


def app(conf):
    "Set up tornado.web.Application() -- only if the ioloop hasn't started"
    ioloop = tornado.ioloop.IOLoop.current()
    if ioloop._running:
        logging.warning('Ignoring app config change when running')
    else:
        info.app = tornado.web.Application(**conf.settings)
        info.app.listen(**conf.listen)

        def callback():
            if ioloop._running:
                return

            logging.info('Listening on port %d', conf.listen.port)

            # browser: True opens the application home page on localhost.
            # browser: url opens the application to a specific URL
            if conf.browser:
                url = 'http://127.0.0.1:%d/' % conf.listen.port
                if isinstance(conf.browser, str):
                    url = urlparse.urljoin(url, conf.browser)
                browser = webbrowser.get()
                logging.info('Opening %s in %s browser', url, browser.__class__.__name__)
                browser.open(url)
            ioloop.start()

        return callback


def schedule(conf):
    "Set up the Gramex PeriodicCallback scheduler"
    scheduler.setup(schedule=conf, tasks=info.schedule)


def _sort_url_patterns(entry):
    # URLs are resolved in this order:
    name, spec = entry
    pattern = spec.pattern
    return (
        spec.get('priority', 0),    # by explicity priority: parameter
        pattern.count('/'),         # by path depth (deeper paths are higher)
        -(pattern.count('*') +
          pattern.count('+')),      # by wildcards (wildcards get lower priority)
    )


def _url_normalize(pattern):
    'Remove double slashes, ../, ./ etc in the URL path. Remove URL fragment'
    url = urlparse.urlsplit(pattern)
    path = posixpath.normpath(url.path)
    if url.path.endswith('/') and not path.endswith('/'):
        path += '/'
    return urlparse.urlunsplit((url.scheme, url.netloc, path, url.query, ''))


class DefaultFormatter(string.Formatter):
    def __init__(self, missing=''):
        self.missing = missing

    def get_field(self, field_name, args, kwargs):
        try:
            val = super(DefaultFormatter, self).get_field(field_name, args, kwargs)
        except (KeyError, AttributeError):
            val = None, field_name
        return val

    def format_field(self, value, spec):
        if value is None:
            return self.missing
        return super(DefaultFormatter, self).format_field(value, spec)


def _cache_generator(conf, name):
    '''
    The ``url:`` section of ``gramex.yaml`` can specify a ``cache:`` section. For
    example::

        url:
            home:
                pattern: /
                handler: ...
                cache:
                    key: {request.uri}{request.cookies[user]}
                    store: memory
                    expires:
                        duration: 1 minute

    This function takes the ``cache`` section of the configuration and returns a
    "cache" function. This function accepts a RequestHandler and returns a
    ``CacheFile`` instance.

    Here's a typical usage::

        cache_method = _cache_generator(conf.cache)     # one-time initialisation
        cache_file = cache_method(handler)              # used inside a hander

    The cache_file instance exposes the following interface::

        cache_file.get()        # returns None
        cache_file.write('abc')
        cache_file.write('def')
        cache_file.close()
        cache_file.get()        # returns 'abcdef'

    The ``key`` can use the following ``request`` attributes:

    - method: HTTP request method, e.g. "GET" or "POST"
    - uri: The requested uri.
    - path: The path portion of `uri`
    - query:  The query portion of `uri`
    - version:  HTTP version specified in request, e.g. "HTTP/1.1"
    - remote_ip: Client's IP address as a string.
    - protocol: The protocol used, either "http" or "https".
    - host: The requested hostname, usually taken from the ``Host`` header.

    ``headers`` and ``args`` can also be used as dictionaries. Missing
    values default to empty strings.
    '''
    # cache: can be True (to use default settings) or False (to disable cache)
    if conf is True:
        conf = {}
    elif conf is False:
        return None

    # Get the store. Defaults to the first store in the cache: section
    default_store = list(info.cache.keys())[0] if len(info.cache) > 0 else None
    store_name = conf.get('store', default_store)
    if store_name not in info.cache:
        logging.warn('url %s: %s store missing', name, store_name)
    store = info.cache.get(store_name)

    key = conf.get('key', '{request.uri}')
    fmt = DefaultFormatter(missing='~').format
    cachefile_class = urlcache.get_cachefile(store)

    def get_cachefile(handler):
        req = handler.request
        keyval = fmt(key, request=req, headers=req.headers, args=req.arguments)
        return cachefile_class(key=keyval, store=store, handler=handler)

    return get_cachefile


def url(conf):
    "Set up the tornado web app URL handlers"
    handlers = []
    # Sort the handlers in descending order of priority
    specs = sorted(conf.items(), key=_sort_url_patterns, reverse=True)
    for name, spec in specs:
        urlspec = AttrDict(spec)
        urlspec.handler = locate(spec.handler, modules=['gramex.handlers'])
        kwargs = urlspec.get('kwargs', {})
        if 'cache' in urlspec:
            kwargs['cache'] = _cache_generator(urlspec['cache'], name=name)
        handlers.append(tornado.web.URLSpec(
            name=name,
            pattern=_url_normalize(urlspec.pattern),
            handler=urlspec.handler,
            kwargs=kwargs,
        ))
    del info.app.handlers[:]
    info.app.named_handlers.clear()
    info.app.add_handlers('.*$', handlers)


def mime(conf):
    "Set up MIME types"
    for ext, type in conf.items():
        mimetypes.add_type(type, ext, strict=True)


def watch(conf):
    "Set up file watchers"
    events = {'on_modified', 'on_created', 'on_deleted', 'on_moved', 'on_any_event'}
    for name, config in conf.items():
        if 'paths' not in config:
            logging.error('No "paths" in watch config: %s', yaml.dump(config))
            continue
        if not set(config.keys()) & events:
            logging.error('No events in watch config: %s', yaml.dump(config))
            continue
        if not isinstance(config['paths'], (list, set, tuple)):
            config['paths'] = [config['paths']]
        for event in events:
            if event in config:
                if not callable(config[event]):
                    config[event] = locate(config[event])
        watcher.watch(name, **config)


def cache(conf):
    "Set up caches"
    caches = {
        'memory': {
            'policy': {
                'default': 'LRUCache',
                'lru': 'LRUCache',
                'lfu': 'LFUCache',
                # 'fifo': 'TBD'
            },
            'size': 20000000,     # 20MiB
        },
        'disk': {
            'policy': {
                'default': 'least-recently-stored',
                'lru': 'least-recently-used',
                'lfu': 'least-frequently-used',
                'fifo': 'least-recently-stored',
            },
            'size': 1000000000,     # 1GiB
        }
    }

    for name, config in conf.items():
        cache_type = config.type.lower()
        if cache_type not in caches:
            logging.warn('cache: %s has unknown type %s', name, config.type)
            continue

        cache_params = caches[cache_type]
        policy = config.get('policy', 'default')
        if policy not in cache_params['policy']:
            logging.warn('%s cache: %s has unknown policy %s', config.type, name, policy)
            continue

        size = config.get('size', cache_params['size'])

        if cache_type == 'memory':
            import cachetools       # noqa: import late for efficiency
            cache_class = getattr(cachetools, cache_params['policy'][policy])
            info.cache[name] = cache_class(maxsize=size, getsizeof=len)

        elif cache_type == 'disk':
            import diskcache        # noqa: import late for efficiency
            path = config.get('path', '.cache-' + name)
            info.cache[name] = diskcache.Cache(
                path, size_limit=size, eviction_policy=cache_params['policy'][policy])
