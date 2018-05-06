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

import re
import os
import sys
import json
import atexit
import signal
import socket
import logging
import datetime
import posixpath
import mimetypes
import threading
import webbrowser
import tornado.web
import gramex.data
import gramex.cache
import logging.config
import concurrent.futures
import six.moves.urllib.parse as urlparse
from six import text_type, string_types
from tornado.template import Template
from orderedattrdict import AttrDict
from gramex import debug, shutdown, __version__
from gramex.transforms import build_transform
from gramex.config import locate, app_log, ioloop_running, app_log_extra
from gramex.cache import urlfetch, cache_key
from gramex.http import OK, NOT_MODIFIED
from . import urlcache
from .ttlcache import MAXTTL
from .emailer import SMTPMailer
from .sms import AmazonSNS, Twilio

# Service information, available as gramex.service after gramex.init() is called
info = AttrDict(
    app=None,
    schedule=AttrDict(),
    alert=AttrDict(),
    cache=AttrDict(),
    # Initialise with a single worker by default. threadpool.workers overrides this
    threadpool=concurrent.futures.ThreadPoolExecutor(1),
    eventlog=AttrDict(),
    email=AttrDict(),
    sms=AttrDict(),
    encrypt=AttrDict(),
    _md=None,
)
_cache = AttrDict()
atexit.register(info.threadpool.shutdown)


def version(conf):
    '''Check if config version is supported. Currently, only 1.0 is supported'''
    if conf != 1.0:
        raise NotImplementedError('version: %s is not supported. Only 1.0', conf)


def log(conf):
    '''Set up logging using Python's standard logging.config.dictConfig()'''
    # Create directories for directories mentioned by handlers if logs are used
    active_handlers = set(conf.get('root', {}).get('handlers', []))
    for logger in conf.get('loggers', {}).values():
        active_handlers |= set(logger.get('handlers', []))
    for handler, handler_conf in conf.get('handlers', {}).items():
        if handler in active_handlers:
            filename = handler_conf.get('filename', None)
            if filename is not None:
                folder = os.path.dirname(os.path.abspath(handler_conf.filename))
                if not os.path.exists(folder):
                    try:
                        os.makedirs(folder)
                    except OSError:
                        app_log.exception('log: %s: cannot create folder %s', handler, folder)
    try:
        logging.config.dictConfig(conf)
    except (ValueError, TypeError, AttributeError, ImportError):
        app_log.exception('Error in log: configuration')


class GramexApp(tornado.web.Application):
    def log_request(self, handler):
        # BaseHandler defines a a custom log format. If that's present, use it.
        if hasattr(handler, 'log_request'):
            handler.log_request()
        # Log the request with the handler name at the end.
        status = handler.get_status()
        if status < 400:                    # noqa: < 400 is any successful request
            log_method = gramex.cache.app_log.info
        elif status < 500:                  # noqa: 400-499 is a user error
            log_method = gramex.cache.app_log.warning
        else:                               # 500+ is a server error
            log_method = gramex.cache.app_log.error
        request_time = 1000.0 * handler.request.request_time()
        handler_name = getattr(handler, 'name', handler.__class__.__name__)
        log_method("%d %s %.2fms %s", handler.get_status(),
                   handler._request_summary(), request_time, handler_name)

    def clear_handlers(self):
        '''
        Clear all handlers in the application.
        (Tornado does not provide a direct way of doing this.)
        '''
        # Up to Tornado 4.4, the handlers attribute stored the handlers
        if hasattr(self, 'handlers'):
            del self.handlers[:]
            self.named_handlers.clear()

        # From Tornado 4.5, there are routers that hold the rules
        else:
            del self.default_router.rules[:]
            del self.wildcard_router.rules[:]


def app(conf):
    '''Set up tornado.web.Application() -- only if the ioloop hasn't started'''
    import tornado.ioloop

    ioloop = tornado.ioloop.IOLoop.current()
    if ioloop_running(ioloop):
        app_log.warning('Ignoring app config change when running')
    else:
        info.app = GramexApp(**conf.settings)
        try:
            info.app.listen(**conf.listen)
        except socket.error as e:
            port_used_codes = dict(windows=10048, linux=98)
            if e.errno not in port_used_codes.values():
                raise
            logging.error('Port %d is busy. Use --listen.port= for a different port',
                          conf.listen.port)
            import sys
            sys.exit(1)

        def callback():
            '''Called after all services are started. Opens browser if required'''
            if ioloop_running(ioloop):
                return

            app_log.info('Listening on port %d', conf.listen.port)
            app_log_extra['port'] = conf.listen.port

            # browser: True opens the application home page on localhost.
            # browser: url opens the application to a specific URL
            url = 'http://127.0.0.1:%d/' % conf.listen.port
            if conf.browser:
                if isinstance(conf.browser, str):
                    url = urlparse.urljoin(url, conf.browser)
                try:
                    browser = webbrowser.get()
                    app_log.info('Opening %s in %s browser', url, browser.__class__.__name__)
                    browser.open(url)
                except webbrowser.Error:
                    app_log.info('Unable to open browser')
            else:
                app_log.info('<Ctrl-B> opens the browser. <Ctrl-D> starts the debugger.')

            # Ensure that we call shutdown() on Ctrl-C.
            # On Windows, Tornado does not exit on Ctrl-C. This also fixes that.
            # When Ctrl-C is pressed, signal_handler() sets _exit to [True].
            # check_exit() periodically watches and calls shutdown().
            # But signal handlers can only be set in the main thread.
            # So ignore if we're not in the main thread (e.g. for nosetests, Windows service)
            #
            # Note: The PeriodicCallback takes up a small amount of CPU time.
            # Note: getch() doesn't handle keyboard buffer queue.
            # Note: This is no guarantee that shutdown() will be called.
            if isinstance(threading.current_thread(), threading._MainThread):
                exit = [False]

                def check_exit():
                    if exit[0] is True:
                        shutdown()
                    # If Ctrl-D is pressed, run the Python debugger
                    char = debug.getch()
                    if char == b'\x04':
                        import ipdb as pdb      # noqa
                        pdb.set_trace()         # noqa
                    # If Ctrl-B is pressed, start the browser
                    if char == b'\x02':
                        browser = webbrowser.get()
                        browser.open(url)

                def signal_handler(signum, frame):
                    exit[0] = True

                try:
                    signal.signal(signal.SIGINT, signal_handler)
                except ValueError:
                    # When running as a Windows Service (winservice.py), python
                    # itself is on a thread, I think. So ignore the
                    # ValueError: signal only works in main thread.
                    pass
                else:
                    tornado.ioloop.PeriodicCallback(check_exit, callback_time=500).start()

            ioloop.start()

        return callback


def _stop_all_tasks(tasks):
    for name, task in tasks.items():
        task.stop()
    tasks.clear()


def schedule(conf):
    '''Set up the Gramex PeriodicCallback scheduler'''
    # Create tasks running on ioloop for the given schedule, store it in info.schedule
    from . import scheduler
    _stop_all_tasks(info.schedule)
    for name, sched in conf.items():
        _key = cache_key('schedule', sched)
        if _key in _cache:
            info.schedule[name] = _cache[_key]
            continue
        try:
            app_log.info('Initialising schedule:%s', name)
            _cache[_key] = scheduler.Task(name, sched, info.threadpool, ioloop=None)
            info.schedule[name] = _cache[_key]
        except Exception as e:
            app_log.exception(e)


def _markdown_convert(content):
    '''
    Convert content into Markdown with extensions.
    '''
    # Cache the markdown converter
    if '_markdown' not in info:
        import markdown
        info['_markdown'] = markdown.Markdown(extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.meta',
            'markdown.extensions.codehilite',
            'markdown.extensions.smarty',
            'markdown.extensions.sane_lists',
            'markdown.extensions.fenced_code',
            'markdown.extensions.toc',
        ], output_format='html5')
    return info['_markdown'].convert(content)


def create_alert(name, alert):
    '''Generate the function to be run by alert() using the alert configuration'''

    # Configure email service
    if alert.get('service', None) is None:
        if len(info.email) > 0:
            alert['service'] = list(info.email.keys())[0]
            app_log.warning('alert: %s: using first email service: %s', name, alert['service'])
        else:
            app_log.error('alert: %s: define an email: service to use', name)
            return
    service = alert['service']
    mailer = info.email.get(service, None)
    if mailer is None:
        app_log.error('alert: %s: undefined email service: %s', name, service)
        return

    # - Warn if to, cc, bcc exists and is not a string or list of strings. Ignore incorrect
    #    - if to: [1, 'user@example.org'], then
    #    - log a warning about the 1. Drop the 1. to: becomes ['user@example.org']

    # Error if to, cc, bcc are all missing, return None
    if not any(key in alert for key in ['to', 'cc', 'bcc']):
        app_log.error('alert: %s: missing to/cc/bcc', name)
        return

    # Warn if subject is missing
    if 'subject' not in alert:
        app_log.warning('alert: %s: missing subject', name)

    # Warn if body, html, bodyfile, htmlfile keys are missing
    contentfields = ['body', 'html', 'bodyfile', 'htmlfile', 'markdown', 'markdownfile']
    if not any(key in alert for key in contentfields):
        app_log.warning('alert: %s: missing body/html/bodyfile/htmlfile/...', name)

    # Precompile templates
    templates = {}
    for key in ['to', 'cc', 'bcc', 'from', 'subject'] + contentfields:
        if key in alert:
            tmpl = alert[key]
            if isinstance(tmpl, string_types):
                templates[key] = Template(tmpl)
            elif isinstance(tmpl, list):
                templates[key] = [Template(subtmpl) for subtmpl in tmpl]
            else:
                app_log.error('alert: %s: %s: %r must be a list or str', name, key, tmpl)
                return

    if 'images' in alert:
        images = alert['images']
        if isinstance(images, dict):
            templates['images'] = {cid: Template(path) for cid, path in images.items()}
        else:
            app_log.error('alert: %s images: %r is not a dict', name, images)
    if 'attachments' in alert:
        attachments = alert['attachments']
        if isinstance(attachments, list):
            templates['attachments'] = [Template(path) for path in attachments]

    # Pre-compile data.
    #   - `data: {key: [...]}` -- loads data in-place
    #   - `data: {key: {url: file}}` -- loads from a file
    #   - `data: {key: {url: sqlalchemy-url, table: table}}` -- loads from a database
    #   - `data: file` -- same as `data: {data: {url: file}}`
    #   - `data: {key: file}` -- same as `data: {key: {url: file}}`
    #   - `data: [...]` -- same as `data: {data: [...]}`
    datasets = {}
    if 'data' in alert:
        if isinstance(alert['data'], string_types):
            datasets = {'data': {'url': alert['data']}}
        elif isinstance(alert['data'], list):
            datasets = {'data': alert['data']}
        elif isinstance(alert['data'], dict):
            for key, dataset in alert['data'].items():
                if isinstance(dataset, string_types):
                    datasets[key] = {'url': dataset}
                elif isinstance(dataset, list) or 'url' in dataset:
                    datasets[key] = dataset
                else:
                    app_log.error('alert: %s data: %s is missing url:', name, key)
        else:
            app_log.error('alert: %s data: must be a data file or dict. Not %s',
                          name, repr(alert['data']))

    if 'each' in alert and alert['each'] not in datasets:
        app_log.error('alert: %s each: %s is not in data:', name, alert['each'])
        return

    vars = {key: None for key in datasets}
    vars['config'] = None
    condition = build_transform(
        {'function': alert.get('condition', 'True')},
        filename='alert: %s' % name, vars=vars, iter=False)

    alert_logger = logging.getLogger('gramex.alert')

    def run_alert(callback=None):
        '''
        Runs the configured alert. If a callback is specified, calls the
        callback with all email arguments. Else sends the email.
        '''
        app_log.info('alert: %s running', name)
        data = {'config': alert}
        for key, dataset in datasets.items():
            # Allow raw data in lists as-is. Treat dicts as {url: ...}
            data[key] = dataset if isinstance(dataset, list) else gramex.data.filter(**dataset)

        result = condition(**data)
        # Avoiding isinstance(result, pd.DataFrame) to avoid importing pandas
        if type(result).__name__ == 'DataFrame':
            data['data'] = result
        elif isinstance(result, dict):
            data.update(result)
        elif not result:
            app_log.debug('alert: %s stopped. condition = %s', name, result)
            return

        each = [(None, None)]
        if 'each' in alert:
            each_data = data[alert['each']]
            if isinstance(each_data, dict):
                each = list(each_data.items())
            elif isinstance(each_data, list):
                each = list(enumerate(each_data))
            elif hasattr(each_data, 'iterrows'):
                each = list(each_data.iterrows())
            else:
                app_log.error('alert: %s: each: requires data.%s to be a dict/list/DataFrame',
                              name, alert['each'])
                return

        kwargslist = []
        for index, row in each:
            data['index'], data['row'], data['config'] = index, row, alert

            # Generate email content
            kwargs = {}
            kwargslist.append(kwargs)
            for key in ['bodyfile', 'htmlfile', 'markdownfile']:
                target = key.replace('file', '')
                if key in templates and target not in templates:
                    path = templates[key].generate(**data).decode('utf-8')
                    tmpl = gramex.cache.open(path, 'template')
                    kwargs[target] = tmpl.generate(**data).decode('utf-8')
            try:
                for key in ['to', 'cc', 'bcc', 'from', 'subject', 'body', 'html', 'markdown']:
                    if key in templates:
                        tmpl = templates[key]
                        if isinstance(tmpl, list):
                            kwargs[key] = []
                            for subtmpl in tmpl:
                                kwargs[key].append(subtmpl.generate(**data).decode('utf-8'))
                        else:
                            kwargs[key] = tmpl.generate(**data).decode('utf-8')
            except Exception:
                # If any template raises an exception, log it and continue with next email
                app_log.exception('alert: %s(#%s).%s: Template exception', name, index, key)
                continue
            headers = {}
            # user: {id: ...} creates an X-Gramex-User header to mimic the user
            if 'user' in alert:
                if 'encrypt' not in info['encrypt']:
                    app_log.error('alert: %s: no encrypt: section. ignoring user: %s',
                                  name, repr(alert['user']))
                else:
                    headers['X-Gramex-User'] = info['encrypt'].encrypt(alert['user'])
            if 'markdown' in kwargs:
                kwargs['html'] = _markdown_convert(kwargs.pop('markdown'))
            if 'images' in templates:
                kwargs['images'] = {
                    cid: urlfetch(val.generate(**data).decode('utf-8'), headers=headers)
                    for cid, val in templates['images'].items()
                }
            if 'attachments' in templates:
                kwargs['attachments'] = [
                    urlfetch(attachment.generate(**data).decode('utf-8'), headers=headers)
                    for attachment in templates['attachments']
                ]
            if callable(callback):
                return callback(**kwargs)
            # Email recipient. TODO: run this in a queue. (Anand)
            mailer.mail(**kwargs)
            # Log the event
            event = {'alert': name, 'service': service, 'from': mailer.email or '',
                     'to': '', 'cc': '', 'bcc': '', 'subject': '',
                     'datetime': datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")}
            event.update({k: v for k, v in kwargs.items() if k in event})
            event['attachments'] = ', '.join(kwargs.get('attachments', []))
            alert_logger.info(event)
        return kwargslist

    return run_alert


def alert(conf):
    from . import scheduler
    _stop_all_tasks(info.alert)
    schedule_keys = 'minutes hours dates months weekdays years startup'.split()

    for name, alert in conf.items():
        _key = cache_key('alert', alert)
        if _key in _cache:
            info.alert[name] = _cache[_key]
            continue
        app_log.info('Initialising alert: %s', name)
        schedule = {key: alert[key] for key in schedule_keys if key in alert}
        if 'thread' in alert:
            schedule['thread'] = alert['thread']
        schedule['function'] = create_alert(name, alert)
        if schedule['function'] is not None:
            try:
                _cache[_key] = scheduler.Task(name, schedule, info.threadpool, ioloop=None)
                info.alert[name] = _cache[_key]
            except Exception:
                app_log.exception('Failed to initialize alert: %s', name)


def threadpool(conf):
    '''Set up a global threadpool executor'''
    # By default, use a single worker. If a different value is specified, use it
    workers = 1
    if conf and hasattr(conf, 'get'):
        workers = conf.get('workers', workers)
    info.threadpool = concurrent.futures.ThreadPoolExecutor(workers)
    atexit.register(info.threadpool.shutdown)


def handlers(conf):
    '''
    The handlers: config is used by the url: handlers to set up the defaults.
    No explicit configuration is required.
    '''
    pass


def _sort_url_patterns(entry):
    '''
    Sort URL patterns based on their specificity. This allows patterns to
    over-ride each other in a CSS-like way.
    '''
    name, spec = entry
    pattern = spec.pattern
    # URLs are resolved in this order:
    return (
        spec.get('priority', 0),    # by explicity priority: parameter
        pattern.count('/'),         # by path depth (deeper paths are higher)
        -(pattern.count('*') +
          pattern.count('+')),      # by wildcards (wildcards get lower priority)
    )
    # TODO: patterns like (js/.*|css/.*|img/.*) will have path depth of 3.
    # But this should really count only as 1.


def _url_normalize(pattern):
    '''Remove double slashes, ../, ./ etc in the URL path. Remove URL fragment'''
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

    - ``request.attr`` => ``request.attr`` can be any request attribute, as str
    - ``header.key`` => ``request.headers[key]``
    - ``cookies.key`` => ``request.cookies[key].value``
    - ``args.key`` => ``handler.args[key]`` joined with a comma.
    - ``user.key`` => ``handler.current_user[key]`` as str

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
            app_log.warning('url: %s: ignoring invalid cache key %s', name, key)
            continue
        # convert second part into a Python string representation
        val = repr(parts[1])
        if parts[0] == 'request':
            key_getters.append('u(getattr(request, %s, missing))' % val)
        elif parts[0].startswith('header'):
            key_getters.append('request.headers.get(%s, missing)' % val)
        elif parts[0].startswith('cookie'):
            key_getters.append(
                'request.cookies[%s].value if %s in request.cookies else missing' % (val, val))
        elif parts[0].startswith('user'):
            key_getters.append('u(handler.current_user.get(%s, missing)) '
                               'if handler.current_user else missing' % val)
        elif parts[0].startswith('arg'):
            key_getters.append('argsep.join(handler.args.get(%s, [missing]))' % val)
        else:
            app_log.warning('url: %s: ignoring invalid cache key %s', name, key)
    # If none of the keys are valid, use the default request key
    if not len(key_getters):
        key_getters = [default_key]

    method = 'def cache_key(handler):\n'
    method += '\trequest = handler.request\n'
    method += '\treturn (%s)' % ', '.join(key_getters)
    context = {
        'missing': '~',
        'argsep': ', ',         # join args using comma
        'u': text_type          # convert to unicode
    }
    # The code is constructed entirely by this function. Using exec is safe
    exec(method, context)       # nosec
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
        app_log.warning('url: %s: store %s missing', name, store_name)
    store = info.cache.get(store_name)

    url_cache_key = _get_cache_key(conf, name)
    cachefile_class = urlcache.get_cachefile(store)
    cache_expiry = conf.get('expiry', {})
    cache_statuses = conf.get('status', [OK, NOT_MODIFIED])
    cache_expiry_duration = cache_expiry.get('duration', MAXTTL)

    # This method will be added to the handler class as "cache", and called as
    # self.cache()
    def get_cachefile(handler):
        return cachefile_class(key=url_cache_key(handler), store=store,
                               handler=handler, expire=cache_expiry_duration,
                               statuses=set(cache_statuses))

    return get_cachefile


def url(conf):
    '''Set up the tornado web app URL handlers'''
    handlers = []
    # Sort the handlers in descending order of priority
    specs = sorted(conf.items(), key=_sort_url_patterns, reverse=True)
    for name, spec in specs:
        _key = cache_key('url', spec)
        if _key in _cache:
            handlers.append(_cache[_key])
            continue
        if 'handler' not in spec:
            app_log.error('url: %s: no handler specified')
            continue
        app_log.debug('url: %s (%s) %s', name, spec.handler, spec.get('priority', ''))
        urlspec = AttrDict(spec)
        handler = locate(spec.handler, modules=['gramex.handlers'])
        if handler is None:
            app_log.error('url: %s: ignoring missing handler %s', name, spec.handler)
            continue

        # Create a subclass of the handler with additional attributes.
        class_vars = {'name': name, 'conf': spec}
        # If there's a cache section, get the cache method for use by BaseHandler
        if 'cache' in urlspec:
            class_vars['cache'] = _cache_generator(urlspec['cache'], name=name)
        else:
            class_vars['cache'] = None
        # PY27 type() requires the class name to be a string, not unicode
        urlspec.handler = type(str(spec.handler), (handler, ), class_vars)

        # If there's a setup method, call it to initialize the class
        kwargs = urlspec.get('kwargs', {})
        if hasattr(handler, 'setup'):
            try:
                urlspec.handler.setup(**kwargs)
            except Exception:
                app_log.exception('url: %s: setup exception in handler %s', name, spec.handler)

        try:
            handler_entry = tornado.web.URLSpec(
                name=name,
                pattern=_url_normalize(urlspec.pattern),
                handler=urlspec.handler,
                kwargs=kwargs,
            )
        except re.error:
            app_log.error('url: %s: pattern: %s is invalid', name, urlspec.pattern)
        except Exception:
            app_log.exception('url: %s: invalid', name)
        _cache[_key] = handler_entry
        handlers.append(handler_entry)

    info.app.clear_handlers()
    info.app.add_handlers('.*$', handlers)


def mime(conf):
    '''Set up MIME types'''
    for ext, type in conf.items():
        mimetypes.add_type(type, ext, strict=True)


def watch(conf):
    '''Set up file watchers'''
    from . import watcher

    events = {'on_modified', 'on_created', 'on_deleted', 'on_moved', 'on_any_event'}
    for name, config in conf.items():
        _key = cache_key('watch', config)
        if _key in _cache:
            watcher.watch(name, **_cache[_key])
            continue
        if 'paths' not in config:
            app_log.error('watch:%s has no "paths"', name)
            continue
        if not set(config.keys()) & events:
            app_log.error('watch:%s has no events (on_modified, ...)', name)
            continue
        if not isinstance(config['paths'], (list, set, tuple)):
            config['paths'] = [config['paths']]
        for event in events:
            if event in config:
                if not callable(config[event]):
                    config[event] = locate(config[event], modules=['gramex.transforms'])
                    if not callable(config[event]):
                        app_log.error('watch:%s.%s is not callable', name, event)
                        config[event] = lambda event: None
        _cache[_key] = config
        watcher.watch(name, **_cache[_key])


def cache(conf):
    '''Set up caches'''
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
            app_log.warning('cache: %s has unknown type %s', name, config.type)
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


def eventlog(conf):
    '''Set up the application event logger'''
    if not conf.path:
        return

    import time
    import sqlite3

    folder = os.path.dirname(os.path.abspath(conf.path))
    if not os.path.exists(folder):
        os.makedirs(folder)
    conn = info.eventlog.conn = sqlite3.connect(conf.path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE IF NOT EXISTS events (time REAL, event TEXT, data TEXT)')
    conn.commit()

    def add(event_name, data):
        '''Write a message into the application event log'''
        data = json.dumps(data, ensure_ascii=True, separators=(',', ':'))
        conn.execute('INSERT INTO events VALUES (?, ?, ?)', [time.time(), event_name, data])
        conn.commit()

    def shutdown():
        add('shutdown', {'version': __version__, 'pid': os.getpid()})
        # Don't close the connection here. gramex.gramex_update() runs in a thread. If we start and
        # stop gramex quickly, allow gramex_update to add too this entry
        # conn.close()

    info.eventlog.add = add
    add('startup', {'version': __version__, 'pid': os.getpid(),
                    'args': sys.argv, 'cwd': os.getcwd()})
    atexit.register(shutdown)


def email(conf):
    '''Set up email service'''
    for name, config in conf.items():
        _key = cache_key('email', config)
        if _key in _cache:
            info.email[name] = _cache[_key]
            continue
        info.email[name] = _cache[_key] = SMTPMailer(**config)


sms_notifiers = {
    'amazonsns': AmazonSNS,
    'twilio': Twilio,
}


def sms(conf):
    '''Set up SMS service'''
    for name, config in conf.items():
        _key = cache_key('sms', config)
        if _key in _cache:
            info.sms[name] = _cache[_key]
            continue
        notifier_type = config.pop('type')
        if notifier_type not in sms_notifiers:
            raise ValueError('sms: %s: Unknown type: %s' % (name, notifier_type))
        info.sms[name] = _cache[_key] = sms_notifiers[notifier_type](**config)


def _get_key_text(path):
    if not os.path.exists(path):
        app_log.error('encrypt: missing file %s', path)
    else:
        with open(path, 'rb') as handle:
            return handle.read()


def encrypt(conf):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import padding
    from base64 import b64decode, b64encode

    backend = default_backend()
    pad = padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None)

    enc = info['encrypt']
    if 'private_key' in conf:
        data = _get_key_text(conf['private_key'])
        if data:
            prv = serialization.load_pem_private_key(data, password=None, backend=backend)
            enc.decrypt = lambda s: json.loads(prv.decrypt(b64decode(s), pad))
    if 'public_key' in conf:
        data = _get_key_text(conf['public_key'])
        if data:
            pub = serialization.load_ssh_public_key(data, backend=backend)
            enc.encrypt = lambda r: b64encode(pub.encrypt(json.dumps(r).encode('utf-8'), pad))
    # Services don't need to return a result, but this is a conveniece for unit tests
    return enc


def test(conf):
    '''Set up test service'''
    # Remove auth: section when running gramex.
    # If there are passwords here, they will not be loaded in memory
    conf.pop('auth', None)
