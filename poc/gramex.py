import scheduler
import logging
import tornado.web
import logging.config
from pathlib import Path
from config import ChainConfig, PathConfig
from confutil import python_name
from orderedattrdict import AttrDict

# gramex.path.source = Path where Gramex is installed
# gramex.path.home = Path where Gramex is running from
path = AttrDict(
    source=Path(__file__).absolute().parent,
    home=Path('.').absolute()
)

# config has the ChainConfig object that loads all configurations
# conf holds the final merged configurations
config = ChainConfig([
    ('default', PathConfig(path.source / 'gramex.yaml')),
    ('base', PathConfig(path.home / 'gramex.yaml')),
    ('app', AttrDict())
])

# Service references
service = AttrDict(conf=AttrDict(), tasks=AttrDict())


# TODO: convert into a class
def init():
    # Reload merged configuration and check for changes
    conf = +config
    if service.conf == conf:
        return

    logging.info('Reconfiguring')
    service.conf = conf

    # Configure logging
    logging.config.dictConfig(conf.log)

    # Configure scheduler
    scheduler.setup(schedule=conf.schedule, tasks=service.tasks)

    # Start application if required
    if 'app' not in service:
        service.app = tornado.web.Application(**service.conf.app.settings)
        service.app.listen(**service.conf.app.listen)

    # Configure URL handlers
    service.handlers = []
    for name, spec in conf.url.items():
        # Make a copy to preserve the original conf
        urlspec = AttrDict(spec)
        urlspec.handler = python_name(spec.handler)
        service.handlers.append(tornado.web.URLSpec(name=name, **urlspec))
    del service.app.handlers[:]
    service.app.named_handlers.clear()
    service.app.add_handlers('.*$', service.handlers)


class TemplateHandler(tornado.web.RequestHandler):
    def initialize(self, **kwargs):
        self.kwargs = kwargs

    def get(self):
        self.write('TemplateHandler:<p>{:s}</p>'.format(
            str(self.kwargs)))
