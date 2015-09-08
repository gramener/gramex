import scheduler
import logging
import tornado.web
import logging.config
from pathlib import Path
from confutil import python_name
from orderedattrdict import AttrDict
from config import ChainConfig, PathConfig

# config has the ChainConfig object that loads all configurations
# conf holds the final merged configurations
config = ChainConfig([
    ('source', PathConfig(Path(__file__).absolute().parent / 'gramex.yaml')),
    ('base', PathConfig(Path('.') / 'gramex.yaml')),
    ('app', AttrDict())
])

# Service configuration references
service = AttrDict(
    conf=AttrDict(log=None, app=None, schedule=None, url=None),
    tasks=AttrDict(),
)


def init(path=None):
    if path is not None:
        config.base = PathConfig(path)

    # Reload merged configuration and check for changes
    conf = +config

    # Configure the logs first for better error reporting
    if service.conf.log != conf.log:
        logging.config.dictConfig(conf.log)
        service.conf.log = conf.log

    # Set up the app -- but only if the IOLoop isn't running yet
    ioloop = tornado.ioloop.IOLoop.current()
    if service.conf.app != conf.app:
        if ioloop._running:
            logging.warn('Ignoring app config change when running')
        else:
            service.app = tornado.web.Application(**conf.app.settings)
            service.app.listen(**conf.app.listen)
            service.conf.app = conf.app

    if service.conf.schedule != conf.schedule:
        scheduler.setup(schedule=conf.schedule, tasks=service.tasks)
        service.conf.schedule = conf.schedule

    if service.conf.url != conf.url:
        config_urls(service.app, conf.url)
        service.conf.url = conf.url


def config_urls(app, conf_url):
    'Set the '
    handlers = []
    for name, spec in conf_url.items():
        urlspec = AttrDict(spec)
        urlspec.handler = python_name(spec.handler)
        handlers.append(tornado.web.URLSpec(name=name, **urlspec))
    del app.handlers[:]
    app.named_handlers.clear()
    app.add_handlers('.*$', handlers)
