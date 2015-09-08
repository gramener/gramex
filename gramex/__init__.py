import logging
import tornado.web
import logging.config
from pathlib import Path
from orderedattrdict import AttrDict
from . import scheduler
from .confutil import python_name
from .config import ChainConfig, PathConfig

__author__ = 'S Anand'
__email__ = 's.anand@gramener.com'
__version__ = '1.0.0'

paths = AttrDict(
    source=Path(__file__).absolute().parent,
    base=Path('.')
)

# conf has the ChainConfig object that loads all configurations
# conf holds the final merged configurations
conf = ChainConfig()

# Service configuration references
service = AttrDict(
    conf=AttrDict(log=None, app=None, schedule=None, url=None),
    tasks=AttrDict(),
)


def init(**kwargs):
    paths.update(kwargs)
    for name, path in paths.items():
        if name not in conf:
            conf[name] = PathConfig(path / 'gramex.yaml')
    if 'app' not in conf:
        conf.app = AttrDict()

    # Reload merged configuration and check for changes
    new_conf = +conf

    # Configure the logs first for better error reporting
    if service.conf.log != new_conf.log:
        logging.config.dictConfig(new_conf.log)

    # Set up the app -- but only if the IOLoop isn't running yet
    ioloop = tornado.ioloop.IOLoop.current()
    if service.conf.app != new_conf.app:
        if ioloop._running:
            logging.warn('Ignoring app config change when running')
        else:
            service.app = tornado.web.Application(**new_conf.app.settings)
            service.app.listen(**new_conf.app.listen)

    if service.conf.schedule != new_conf.schedule:
        scheduler.setup(schedule=new_conf.schedule, tasks=service.tasks)

    if service.conf.url != new_conf.url:
        config_urls(service.app, new_conf.url)

    service.conf = new_conf


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


def run():
    init()
    tornado.ioloop.IOLoop.current().start()
