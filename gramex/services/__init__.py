'''
This module is a service registry for ``gramex.yaml``. Each key must have a
corresponding function in this file.

For example, if ``gramex.yaml`` contains this section::

    log:
        version: 1


... then :func:`log` is called as ``log({"version": 1})``. If no such function
exists, a warning is raised.
'''

import logging
import tornado.web
from orderedattrdict import AttrDict
from zope.dottedname.resolve import resolve
from . import scheduler


info = AttrDict(
    ioloop=tornado.ioloop.IOLoop.current(),
    app=None,
    tasks=AttrDict(),
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
    if info.ioloop._running:
        logging.warn('Ignoring app config change when running')
    else:
        info.app = tornado.web.Application(**conf.settings)
        info.app.listen(**conf.listen)


def schedule(conf):
    "Set up the Gramex PeriodicCallback scheduler"
    scheduler.setup(schedule=conf, tasks=info.tasks)


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
