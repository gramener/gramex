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
import logging
import posixpath
import mimetypes
import webbrowser
import tornado.web
import tornado.ioloop
import six.moves.urllib.parse as urlparse
from orderedattrdict import AttrDict
from . import scheduler
from . import watcher
from ..config import locate


# Service-specific information
info = AttrDict(
    app=None,
    schedule=AttrDict(),
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


def url(conf):
    "Set up the tornado web app URL handlers"
    handlers = []
    # Sort the handlers in descending order of priority
    specs = sorted(conf.items(), key=_sort_url_patterns, reverse=True)
    for name, spec in specs:
        urlspec = AttrDict(spec)
        urlspec.handler = locate(spec.handler, modules=['gramex.handlers'])
        handlers.append(tornado.web.URLSpec(
            name=name,
            pattern=_url_normalize(urlspec.pattern),
            handler=urlspec.handler,
            kwargs=urlspec.get('kwargs', None)))
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
