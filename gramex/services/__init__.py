'''
This module is a service registry for ``gramex.yaml``. Each key must have a
corresponding function in this file.

For example, if ``gramex.yaml`` contains this section::

    log:
        version: 1


... then :func:`log` is called as ``log({"version": 1})``. If no such function
exists, a warning is raised.
'''

import gramex
import mimetypes
import logging.config
import tornado.web
import tornado.ioloop
from orderedattrdict import AttrDict
from zope.dottedname.resolve import resolve
from . import scheduler
from . import watcher


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
    if tornado.ioloop.IOLoop.current()._running:
        logging.warn('Ignoring app config change when running')
    else:
        info.app = tornado.web.Application(**conf.settings)
        info.app.listen(**conf.listen)


def schedule(conf):
    "Set up the Gramex PeriodicCallback scheduler"
    scheduler.setup(schedule=conf, tasks=info.schedule)


def url(conf):
    "Set up the tornado web app URL handlers"
    handlers = []
    for name, spec in conf.items():
        urlspec = AttrDict(spec)
        urlspec.handler = resolve(spec.handler)
        handlers.append(tornado.web.URLSpec(name=name, **urlspec))
    del info.app.handlers[:]
    info.app.named_handlers.clear()
    info.app.add_handlers('.*$', handlers)


def mime(conf):
    "Set up MIME types"
    for ext, type in conf.items():
        mimetypes.add_type(type, ext, strict=True)

def watch(conf):
    "Set up file watchers"
    watcher.watch(
        'gramex-reconfigure',
        paths=[pathinfo.path
               for pathconfig in gramex.config_layers.values()
               for pathinfo in pathconfig.__info__.imports],
        on_modified=lambda event: gramex.init())
