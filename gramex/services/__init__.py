'''
This module is a service registry for ``gramex.yaml``. Each key must have a
corresponding function in this file.

For example, if ``gramex.yaml`` contains this section::

    log:
        version: 1


... then :func:`log` is called as ``log({"version": 1})``. If no such function
exists, a warning is raised.
'''
from __future__ import unicode_literals

import yaml
import atexit
import signal
import posixpath
import mimetypes
import threading
import webbrowser
import tornado.web
import tornado.ioloop
import logging.config
import concurrent.futures
import six.moves.urllib.parse as urlparse
from six.moves import http_client
from orderedattrdict import AttrDict
from . import scheduler
from . import watcher
from . import urlcache
from .. import debug
from .. import shutdown
from .ttlcache import MAXTTL
from ..config import locate, app_log


# Service-specific information
info = AttrDict(
    app=None,
    schedule=AttrDict(),
    cache=AttrDict(),
    # Initialise with a single worker by default. threadpool.workers overrides this
    threadpool=concurrent.futures.ThreadPoolExecutor(1),
)
atexit.register(info.threadpool.shutdown)


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
        app_log.warning('Ignoring app config change when running')
    else:
        info.app = tornado.web.Application(**conf.settings)
        info.app.listen(**conf.listen)

        def callback():
            'Called after all services are started. Opens browser if required'
            if ioloop._running:
                return

            app_log.info('Listening on port %d', conf.listen.port)

            # browser: True opens the application home page on localhost.
            # browser: url opens the application to a specific URL
            if conf.browser:
                url = 'http://127.0.0.1:%d/' % conf.listen.port
                if isinstance(conf.browser, str):
                    url = urlparse.urljoin(url, conf.browser)
                browser = webbrowser.get()
                app_log.info('Opening %s in %s browser', url, browser.__class__.__name__)
                browser.open(url)

            # Ensure that we call shutdown() on Ctrl-C.
            # On Windows, Tornado does not exit on Ctrl-C. This also fixes that.
            # When Ctrl-C is pressed, signal_handler() sets _exit to [True].
            # check_exit() periodically watches and calls shutdown().
            # But signal handlers can only be set in the main thread.
            # So ignore if we're not in the main thread (e.g. for nosetests.)
            if isinstance(threading.current_thread(), threading._MainThread):
                exit = [False]

                def check_exit():
                    if exit[0] is True:
                        shutdown()
                    # If Ctrl-D is pressed, run the Python debugger
                    if debug.getch() == '\x04' and conf.get('pdb', False):
                        import ipdb as pdb
                        pdb.set_trace()

                def signal_handler(signum, frame):
                    exit[0] = True

                signal.signal(signal.SIGINT, signal_handler)
                tornado.ioloop.PeriodicCallback(check_exit, callback_time=500).start()

            ioloop.start()

        return callback


def schedule(conf):
    "Set up the Gramex PeriodicCallback scheduler"
    scheduler.setup(schedule=conf, tasks=info.schedule, threadpool=info.threadpool)


def threadpool(conf):
    "Set up a global threadpool executor"
    # By default, use a single worker. If a different value is specified, use it
    workers = 1
    if conf and hasattr(conf, 'get'):
        workers = conf.get('workers', workers)
    info.threadpool = concurrent.futures.ThreadPoolExecutor(workers)
    atexit.register(info.threadpool.shutdown)


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


def _get_cache_key(conf, name):
    '''
    Parse the cache.key parameter. Return a function that takes the request and
    returns the cache key value.

    The cache key is a string or a list of strings. The strings can be:

    - ``request.attr`` => ``request.attr`` can be any request attribute.
    - ``header.key`` => ``request.headers[key]``
    - ``cookies.key`` => ``request.cookies[key].value``
    - ``args.key`` => ``requst.arguments[key]`` joined with a comma.

    Invalid key strings are ignored with a warning. If all key strings are
    invalid, the default cache.key of ``request.uri`` is used.
    '''
    default_key = 'request.uri'
    keys = conf.get('key', default_key)
    if not isinstance(keys, list):
        keys = [keys]
    key_getters = []
    for key in keys:
        parts = key.split('.', 2)
        if len(parts) < 2:
            app_log.warn('url %s: ignoring invalid cache key %s', name, key)
            continue
        # convert second part into a Python string representation
        val = repr(parts[1])
        if parts[0] == 'request':
            key_getters.append('getattr(request, %s, missing)' % val)
        elif parts[0].startswith('header'):
            key_getters.append('request.headers.get(%s, missing)' % val)
        elif parts[0].startswith('cookie'):
            key_getters.append(
                'request.cookies[%s].value if %s in request.cookies else missing' % (val, val))
        elif parts[0].startswith('arg'):
            key_getters.append('argsep.join(request.arguments.get(%s, [missing_b]))' % val)
        else:
            app_log.warn('url %s: ignoring invalid cache key %s', name, key)
    # If none of the keys are valid, use the default request key
    if not len(key_getters):
        key_getters = [default_key]

    method = 'def cache_key(request):\n'
    method += '\treturn (%s)' % ', '.join(key_getters)
    context = {
        'missing': '~',
        'missing_b': b'~',      # args are binary
        'argsep': b', ',        # join args using binary comma
    }
    exec(method, context)
    return context['cache_key']


def _cache_generator(conf, name):
    '''
    The ``url:`` section of ``gramex.yaml`` can specify a ``cache:`` section. For
    example::

        url:
            home:
                pattern: /
                handler: ...
                cache:
                    key: request.uri
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
        app_log.warn('url %s: %s store missing', name, store_name)
    store = info.cache.get(store_name)

    cache_key = _get_cache_key(conf, name)
    cachefile_class = urlcache.get_cachefile(store)
    cache_expiry = conf.get('expiry', {})
    cache_statuses = conf.get('status', [http_client.OK])
    cache_expiry_duration = cache_expiry.get('duration', MAXTTL)

    # This method will be added to the handler class as "cache", and called as
    # self.cache()
    def get_cachefile(handler):
        return cachefile_class(key=cache_key(handler.request), store=store,
                               handler=handler, expire=cache_expiry_duration,
                               statuses=set(cache_statuses))

    return get_cachefile


def url(conf):
    "Set up the tornado web app URL handlers"
    handlers = []
    # Sort the handlers in descending order of priority
    specs = sorted(conf.items(), key=_sort_url_patterns, reverse=True)
    for name, spec in specs:
        urlspec = AttrDict(spec)
        handler = locate(spec.handler, modules=['gramex.handlers'])

        # Create a subclass of the handler with additional attributes.
        class_vars = {'name': name, 'conf': spec}
        # If there's a cache section, get the cache method for use by BaseHandler
        if 'cache' in urlspec:
            class_vars['cache'] = _cache_generator(urlspec['cache'], name=name)
        else:
            class_vars['cache'] = None
        urlspec.handler = type(spec.handler, (handler, ), class_vars)

        # If there's a setup method, call it to initialize the class
        kwargs = urlspec.get('kwargs', {})
        if hasattr(handler, 'setup'):
            urlspec.handler.setup(**kwargs)

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
            app_log.error('No "paths" in watch config: %s', yaml.dump(config))
            continue
        if not set(config.keys()) & events:
            app_log.error('No events in watch config: %s', yaml.dump(config))
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
    cache_types = {
        'memory': {
            'size': 20000000,       # 20MiB
        },
        'disk': {
            'size': 1000000000,     # 1GiB
        }
    }

    for name, config in conf.items():
        cache_type = config.type.lower()
        if cache_type not in cache_types:
            app_log.warn('cache: %s has unknown type %s', name, config.type)
            continue

        cache_params = cache_types[cache_type]
        size = config.get('size', cache_params['size'])

        if cache_type == 'memory':
            info.cache[name] = urlcache.MemoryCache(maxsize=size, getsizeof=len)

        elif cache_type == 'disk':
            path = config.get('path', '.cache-' + name)
            info.cache[name] = urlcache.DiskCache(
                path, size_limit=size, eviction_policy='least-recently-stored')
            atexit.register(info.cache[name].close)
