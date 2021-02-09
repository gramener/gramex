'''
This module is a service registry for ``gramex.yaml``. Each key must have a
corresponding function in this file.

For example, if ``gramex.yaml`` contains this section::

    log:
        version: 1

... then :func:`log` is called as ``log({"version": 1})``. If no such function
exists, a warning is raised.
'''
import io
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
import tornado.ioloop
import gramex.data
import gramex.cache
import gramex.license
import logging.config
import concurrent.futures
from copy import deepcopy
from urllib.parse import urljoin, urlsplit, urlunsplit
from tornado.template import Template
from orderedattrdict import AttrDict
from gramex import debug, shutdown, __version__
from gramex.transforms import build_transform
from gramex.config import locate, app_log, ioloop_running, app_log_extra, merge, walk
from gramex.cache import urlfetch, cache_key
from gramex.http import OK, NOT_MODIFIED
from . import urlcache
from .ttlcache import MAXTTL
from .emailer import SMTPMailer
from .sms import AmazonSNS, Exotel, Twilio

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
    gramexlog=AttrDict(apps=AttrDict()),
    url=AttrDict(),
    _md=None,
    _main_ioloop=None,
)
_cache, _tmpl_cache = AttrDict(), AttrDict()
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
            sys.exit(1)

        def callback():
            '''Called after all services are started. Opens browser if required'''
            if ioloop_running(ioloop):
                return

            # If enterprise version is installed, user must accept license
            try:
                import gramexenterprise         # noqa
                gramex.license.accept()
            except ImportError:
                pass

            app_log.info('Listening on port %d', conf.listen.port)
            app_log_extra['port'] = conf.listen.port

            # browser: True opens the application home page on localhost.
            # browser: url opens the application to a specific URL
            url = 'http://127.0.0.1:%d/' % conf.listen.port
            if conf.browser:
                if isinstance(conf.browser, str):
                    url = urljoin(url, conf.browser)
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

            info._main_ioloop = ioloop
            ioloop.start()

        return callback


def _stop_all_tasks(tasks):
    for name, task in tasks.items():
        task.stop()
    tasks.clear()


def schedule(conf):
    '''Set up the Gramex scheduler'''
    # Create tasks running on ioloop for the given schedule, store it in info.schedule
    from . import scheduler
    _stop_all_tasks(info.schedule)
    for name, sched in conf.items():
        _key = cache_key('schedule', sched)
        if _key in _cache:
            task = info.schedule[name] = _cache[_key]
            task.call_later()
            continue
        try:
            app_log.info('Initialising schedule:%s', name)
            _cache[_key] = scheduler.Task(name, sched, info.threadpool,
                                          ioloop=info._main_ioloop)
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


def _tmpl(template_string):
    '''Compile Tornado template. Cache the results'''
    if template_string not in _tmpl_cache:
        _tmpl_cache[template_string] = Template(template_string)
    return _tmpl_cache[template_string]


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
    # Ensure that config has the right type (str, dict, list)
    contentfields = ['body', 'html', 'bodyfile', 'htmlfile', 'markdown', 'markdownfile']
    addr_fields = ['to', 'cc', 'bcc', 'reply_to', 'on_behalf_of', 'from']
    for key in ['subject'] + addr_fields + contentfields:
        if not isinstance(alert.get(key, ''), (str, list)):
            app_log.error('alert: %s.%s: %r must be a list or str', name, key, alert[key])
            return
    if not isinstance(alert.get('images', {}), dict):
        app_log.error('alert: %s.images: %r is not a dict', name, alert['images'])
        return
    if not isinstance(alert.get('attachments', []), list):
        app_log.error('alert: %s.attachments: %r is not a list', name, alert['attachments'])
        return

    # Warn if subject is missing
    if 'subject' not in alert:
        app_log.warning('alert: %s: missing subject', name)

    # Warn if body, html, bodyfile, htmlfile keys are missing
    if not any(key in alert for key in contentfields):
        app_log.warning('alert: %s: missing body/html/bodyfile/htmlfile/...', name)

    # Pre-compile data.
    #   - `data: {key: [...]}` -- loads data in-place
    #   - `data: {key: {url: file}}` -- loads from a file
    #   - `data: {key: {url: sqlalchemy-url, table: table}}` -- loads from a database
    #   - `data: file` -- same as `data: {data: {url: file}}`
    #   - `data: {key: file}` -- same as `data: {key: {url: file}}`
    #   - `data: [...]` -- same as `data: {data: [...]}`
    datasets = {}
    if 'data' in alert:
        if isinstance(alert['data'], str):
            datasets = {'data': {'url': alert['data']}}
        elif isinstance(alert['data'], list):
            datasets = {'data': alert['data']}
        elif isinstance(alert['data'], dict):
            for key, dataset in alert['data'].items():
                if isinstance(dataset, str):
                    datasets[key] = {'url': dataset}
                elif isinstance(dataset, list) or 'url' in dataset:
                    datasets[key] = dataset
                else:
                    app_log.error('alert: %s.data: %s is missing url:', name, key)
        else:
            app_log.error('alert: %s.data: must be a data file or dict. Not %s',
                          name, repr(alert['data']))

    if 'each' in alert and alert['each'] not in datasets:
        app_log.error('alert: %s.each: %s is not in data:', name, alert['each'])
        return

    vars = {key: None for key in datasets}
    vars.update({'config': None, 'args': None})
    condition = build_transform(
        {'function': alert.get('condition', 'True')},
        filename='alert: %s' % name, vars=vars, iter=False)

    alert_logger = logging.getLogger('gramex.alert')

    def load_datasets(data, each):
        '''
        Modify data by load datasets and filter by condition.
        Modify each to apply the each: argument, else return (None, None)
        '''
        for key, val in datasets.items():
            # Allow raw data in lists as-is. Treat dicts as {url: ...}
            data[key] = val if isinstance(val, list) else gramex.data.filter(**val)
        result = condition(**data)
        # Avoiding isinstance(result, pd.DataFrame) to avoid importing pandas
        if type(result).__name__ == 'DataFrame':
            data['data'] = result
        elif isinstance(result, dict):
            data.update(result)
        elif not result:
            app_log.debug('alert: %s stopped. condition = %s', name, result)
            return
        if 'each' in alert:
            each_data = data[alert['each']]
            if isinstance(each_data, dict):
                each += list(each_data.items())
            elif isinstance(each_data, list):
                each += list(enumerate(each_data))
            elif hasattr(each_data, 'iterrows'):
                each += list(each_data.iterrows())
            else:
                raise ValueError('alert: %s: each: data.%s must be dict/list/DF, not %s' % (
                                 name, alert['each'], type(each_data)))
        else:
            each.append((0, None))

    def create_mail(data):
        '''
        Return kwargs that can be passed to a mailer.mail
        '''
        mail = {}
        for key in ['bodyfile', 'htmlfile', 'markdownfile']:
            target = key.replace('file', '')
            if key in alert and target not in alert:
                path = _tmpl(alert[key]).generate(**data).decode('utf-8')
                tmpl = gramex.cache.open(path, 'template')
                mail[target] = tmpl.generate(**data).decode('utf-8')
        for key in addr_fields + ['subject', 'body', 'html', 'markdown']:
            if key not in alert:
                continue
            if isinstance(alert[key], list):
                mail[key] = [_tmpl(v).generate(**data).decode('utf-8') for v in alert[key]]
            else:
                mail[key] = _tmpl(alert[key]).generate(**data).decode('utf-8')
        headers = {}
        # user: {id: ...} creates an X-Gramex-User header to mimic the user
        if 'user' in alert:
            user = deepcopy(alert['user'])
            for key, val, node in walk(user):
                node[key] = _tmpl(val).generate(**data).decode('utf-8')
            user = json.dumps(user, ensure_ascii=True, separators=(',', ':'))
            headers['X-Gramex-User'] = tornado.web.create_signed_value(
                info.app.settings['cookie_secret'], 'user', user)
        if 'markdown' in mail:
            mail['html'] = _markdown_convert(mail.pop('markdown'))
        if 'images' in alert:
            mail['images'] = {}
            for cid, val in alert['images'].items():
                urlpath = _tmpl(val).generate(**data).decode('utf-8')
                urldata = urlfetch(urlpath, info=True, headers=headers)
                if urldata['content_type'].startswith('image/'):
                    mail['images'][cid] = urldata['name']
                else:
                    with io.open(urldata['name'], 'rb') as temp_file:
                        bytestoread = 80
                        first_line = temp_file.read(bytestoread)
                    # TODO: let admin know that the image was not processed
                    app_log.error('alert: %s: %s: %d (%s) not an image: %s\n%r', name,
                                  cid, urldata['r'].status_code, urldata['content_type'],
                                  urlpath, first_line)
        if 'attachments' in alert:
            mail['attachments'] = [
                urlfetch(_tmpl(v).generate(**data).decode('utf-8'), headers=headers)
                for v in alert['attachments']
            ]
        return mail

    def run_alert(callback=None, args=None):
        '''
        Runs the configured alert. If a callback is specified, calls the
        callback with all email arguments. Else sends the email.
        If args= is specified, add it as data['args'].
        '''
        app_log.info('alert: %s running', name)
        data, each, fail = {'config': alert, 'args': {} if args is None else args}, [], []
        try:
            load_datasets(data, each)
        except Exception as e:
            app_log.exception('alert: %s data processing failed', name)
            fail.append({'error': e})

        retval = []
        for index, row in each:
            data['index'], data['row'], data['config'] = index, row, alert
            try:
                retval.append(AttrDict(index=index, row=row, mail=create_mail(data)))
            except Exception as e:
                app_log.exception('alert: %s[%s] templating (row=%r)', name, index, row)
                fail.append({'index': index, 'row': row, 'error': e})

        callback = mailer.mail if not callable(callback) else callback
        done = []
        for v in retval:
            try:
                callback(**v.mail)
            except Exception as e:
                fail.append({'index': v.index, 'row': v.row, 'mail': v.mail, 'error': e})
                app_log.exception('alert: %s[%s] delivery (row=%r)', name, v.index, v.row)
            else:
                done.append(v)
                event = {
                    'alert': name, 'service': service, 'from': mailer.email or '',
                    'to': '', 'cc': '', 'bcc': '', 'subject': '',
                    'datetime': datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
                }
                event.update({k: v for k, v in v.mail.items() if k in event})
                event['attachments'] = ', '.join(v.mail.get('attachments', []))
                alert_logger.info(event)

        # Run notifications
        args = {'done': done, 'fail': fail}
        for notification_name in alert.get('notify', []):
            notify = info.alert.get(notification_name)
            if notify is not None:
                notify.run(callback=callback, args=args)
            else:
                app_log.error('alert: %s.notify: alert %s not defined', name, notification_name)
        return args

    return run_alert


def alert(conf):
    from . import scheduler
    _stop_all_tasks(info.alert)
    schedule_keys = 'minutes hours dates months weekdays years startup utc'.split()

    for name, alert in conf.items():
        _key = cache_key('alert', alert)
        if _key in _cache:
            task = info.alert[name] = _cache[_key]
            task.call_later()
            continue
        app_log.info('Initialising alert: %s', name)
        schedule = {key: alert[key] for key in schedule_keys if key in alert}
        if 'thread' in alert:
            schedule['thread'] = alert['thread']
        schedule['function'] = create_alert(name, alert)
        if schedule['function'] is not None:
            try:
                _cache[_key] = scheduler.Task(name, schedule, info.threadpool,
                                              ioloop=info._main_ioloop)
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
    url = urlsplit(pattern)
    path = posixpath.normpath(url.path)
    if url.path.endswith('/') and not path.endswith('/'):
        path += '/'
    return urlunsplit((url.scheme, url.netloc, path, url.query, ''))


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
        'u': str                # convert to unicode
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
    info.url = {}
    # Sort the handlers in descending order of priority
    specs = sorted(conf.items(), key=_sort_url_patterns, reverse=True)
    for name, spec in specs:
        _key = cache_key('url', spec)
        if _key in _cache:
            info.url[name] = _cache[_key]
            continue
        # service: is an alias for handler: and has higher priority
        if 'service' in spec:
            spec.handler = spec.service
        if 'handler' not in spec:
            app_log.error('url: %s: no service: or handler: specified')
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
                urlspec.handler.setup_default_kwargs()
                urlspec.handler.setup(**kwargs)
            except Exception:
                app_log.exception('url: %s: setup exception in handler %s', name, spec.handler)
                # Since we can't set up the handler, all requests must report the error instead
                class_vars['exc_info'] = sys.exc_info()
                error_handler = locate('SetupFailedHandler', modules=['gramex.handlers'])
                urlspec.handler = type(str(spec.handler), (error_handler, ), class_vars)
                urlspec.handler.setup(**kwargs)

        try:
            handler_entry = tornado.web.URLSpec(
                name=name,
                pattern=_url_normalize(urlspec.pattern),
                handler=urlspec.handler,
                kwargs=kwargs,
            )
        except re.error:
            app_log.error('url: %s: pattern: %s is invalid', name, urlspec.pattern)
            continue
        except Exception:
            app_log.exception('url: %s: invalid', name)
            continue
        info.url[name] = _cache[_key] = handler_entry

    info.app.clear_handlers()
    info.app.add_handlers('.*$', info.url.values())


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


_cache_defaults = {
    'memory': {
        'size': 500000000,      # 500 MiB
    },
    'disk': {
        'size': 10000000000,    # 10 GiB
    },
    'redis': {
        'size': 500000000,      # 500 MiB
    }
}


def cache(conf):
    '''Set up caches'''
    for name, config in conf.items():
        cache_type = config['type']
        if cache_type not in _cache_defaults:
            app_log.warning('cache: %s has unknown type %s', name, config.type)
            continue
        config = merge(dict(config), _cache_defaults[cache_type], mode='setdefault')
        if cache_type == 'memory':
            info.cache[name] = urlcache.MemoryCache(
                maxsize=config['size'], getsizeof=gramex.cache.sizeof)
        elif cache_type == 'disk':
            path = config.get('path', '.cache-' + name)
            info.cache[name] = urlcache.DiskCache(
                path, size_limit=config['size'], eviction_policy='least-recently-stored')
            atexit.register(info.cache[name].close)
        elif cache_type == 'redis':
            path = config['path'] if 'path' in config else None
            try:
                info.cache[name] = urlcache.RedisCache(path=path, maxsize=config['size'])
            except Exception:
                app_log.exception('cache: %s cannot connect to redis', name)
        # if default: true, make this the default cache for gramex.cache.{open,query}
        if config.get('default'):
            for key in ['_OPEN_CACHE', '_QUERY_CACHE']:
                val = gramex.cache.set_cache(info.cache[name], getattr(gramex.cache, key))
                setattr(gramex.cache, key, val)


def eventlog(conf):
    '''Set up the application event logger'''
    if not conf.path:
        return

    import time
    import sqlite3

    folder = os.path.dirname(os.path.abspath(conf.path))
    if not os.path.exists(folder):
        os.makedirs(folder)

    def query(q, *args, **kwargs):
        conn = sqlite3.connect(conf.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        result = list(conn.execute(q, *args, **kwargs))
        conn.commit()
        conn.close()
        return result

    def add(event_name, data):
        '''Write a message into the application event log'''
        data = json.dumps(data, ensure_ascii=True, separators=(',', ':'))
        query('INSERT INTO events VALUES (?, ?, ?)', [time.time(), event_name, data])

    def shutdown():
        add('shutdown', {'version': __version__, 'pid': os.getpid()})
        # Don't close the connection here. gramex.gramex_update() runs in a thread. If we start and
        # stop gramex quickly, allow gramex_update to add too this entry
        # conn.close()

    info.eventlog.query = query
    info.eventlog.add = add

    query('CREATE TABLE IF NOT EXISTS events (time REAL, event TEXT, data TEXT)')
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
    'exotel': Exotel,
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


def encrypt(conf):
    app_log.warning('encrypt: service deprecated.')


def test(conf):
    '''Set up test service'''
    # Remove auth: section when running gramex.
    # If there are passwords here, they will not be loaded in memory
    conf.pop('auth', None)


def gramexlog(conf):
    '''Set up gramexlog service'''
    from gramex.transforms import build_log_info
    try:
        from elasticsearch import Elasticsearch, helpers
    except ImportError:
        app_log.error('gramexlog: elasticsearch missing. pip install elasticsearch')
        return

    # We call push() every 'flush' seconds on the main IOLoop. Defaults to every 5 seconds
    flush = conf.pop('flush', 5)
    ioloop = info._main_ioloop or tornado.ioloop.IOLoop.current()
    # Set the defaultapp to the first config key under gramexlog:
    if len(conf):
        info.gramexlog.defaultapp = next(iter(conf.keys()))
    for app, app_conf in conf.items():
        app_config = info.gramexlog.apps[app] = AttrDict()
        app_config.queue = []
        keys = app_conf.pop('keys', [])
        # If user specifies keys: [port, args.x, ...], these are captured as additional keys.
        # The keys use same spec as Gramex logging.
        app_config.extra_keys = build_log_info(keys)
        # Ensure all gramexlog keys are popped from app_conf, leaving only Elasticsearch keys
        app_config.conn = Elasticsearch(**app_conf)

    def push():
        for app, app_config in info.gramexlog.apps.items():
            for item in app_config.queue:
                item['_index'] = app_config.get('index', app)
            try:
                helpers.bulk(app_config.conn, app_config.queue)
                app_config.queue.clear()
            except Exception:
                # TODO: If the connection broke, re-create it
                # This generic exception should be caught for thread to continue its execution
                app_log.exception('gramexlog: push to %s failed', app)
        if 'handle' in info.gramexlog:
            ioloop.remove_timeout(info.gramexlog.handle)
        # Call again after flush seconds
        info.gramexlog.handle = ioloop.call_later(flush, push)

    info.gramexlog.handle = ioloop.call_later(flush, push)
    info.gramexlog.push = push
