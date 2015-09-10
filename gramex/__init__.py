import logging
import tornado.ioloop
from pathlib import Path
from orderedattrdict import AttrDict
from . import services
from gramex.config import ChainConfig, PathConfig

__author__ = 'S Anand'
__email__ = 's.anand@gramener.com'
__version__ = '1.0.2'

paths = AttrDict([
    ('source', Path(__file__).absolute().parent),
    ('base', Path('.')),
])

# conf holds the final merged configurations
conf = AttrDict()

# The ChainConfig object that loads all configurations. init() updates it
_config_chain = ChainConfig()


def init(**kwargs):
    # Initialise configuration layers with provided paths
    paths.update(kwargs)
    for name, path in paths.items():
        if name not in _config_chain:
            _config_chain[name] = PathConfig(path / 'gramex.yaml')

    # Run all valid services. (The "+" before config_chain merges the chain.)
    for key, val in (+_config_chain).items():
        if key not in conf or conf[key] != val:
            if hasattr(services, key):
                conf[key] = val
                getattr(services, key)(conf[key])
            else:
                logging.warning('No service named %s', key)

    # Start the IOLoop. TODO: can the app service start this delayed?
    ioloop = tornado.ioloop.IOLoop.current()
    if not ioloop._running:
        ioloop.start()
