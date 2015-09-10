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
    "Ensure that we're parsing a supported config version"
    if conf != 1.0:
        raise NotImplementedError('version: %s is not supported. Only 1.0', conf)


def log(conf):
    'Set up logging'
    logging.config.dictConfig(conf)


def app(conf):
    "Set up the Tornado app -- but only if the IOLoop isn't running yet"
    if info.ioloop._running:
        logging.warn('Ignoring app config change when running')
    else:
        info.app = tornado.web.Application(**conf.settings)
        info.app.listen(**conf.listen)


def schedule(conf):
    'Set up the scheduler'
    scheduler.setup(schedule=conf, tasks=info.tasks)


def url(conf):
    'Set the URL handlers'
    handlers = []
    for name, spec in conf.items():
        urlspec = AttrDict(spec)
        urlspec.handler = resolve(spec.handler)
        handlers.append(tornado.web.URLSpec(name=name, **urlspec))
    del info.app.handlers[:]
    info.app.named_handlers.clear()
    info.app.add_handlers('.*$', handlers)
