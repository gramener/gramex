import logging
import tornado.ioloop
from pathlib import Path
from orderedattrdict import AttrDict
from . import services
from gramex.config import ChainConfig, PathConfig

__author__ = 'S Anand'
__email__ = 's.anand@gramener.com'
__version__ = '1.0.2'

paths = AttrDict()              # paths where configurations are stored
conf = AttrDict()               # holds the final merged configurations
config_layers = ChainConfig()   # Loads all configurations. init() updates it

paths['source'] = Path(__file__).absolute().parent
paths['base'] = Path('.')


def init(**kwargs):
    # Initialise configuration layers with provided paths
    paths.update(kwargs)
    for name, path in paths.items():
        if name not in config_layers:
            config_layers[name] = PathConfig(path / 'gramex.yaml')

    # Run all valid services. (The "+" before config_chain merges the chain)
    for key, val in (+config_layers).items():
        if key not in conf or conf[key] != val:
            if hasattr(services, key):
                conf[key] = val
                getattr(services, key)(conf[key])
            else:
                logging.warning('No service named %s', key)

    # Start the IOLoop. TODO: can the app service start this delayed?
    ioloop = tornado.ioloop.IOLoop.current()
    if not ioloop._running:
        logging.info('Listening on port %d', conf.app.listen.port)
        ioloop.start()
