import sys
import json
import logging
import tornado.ioloop
from pathlib import Path
from orderedattrdict import AttrDict
from . import services
from gramex.config import ChainConfig, PathConfig

paths = AttrDict()              # Paths where configurations are stored
conf = AttrDict()               # Final merged configurations
config_layers = ChainConfig()   # Loads all configurations. init() updates it

paths['source'] = Path(__file__).absolute().parent      # Where gramex source code is
paths['base'] = Path('.')                               # Where gramex is run from

# Populate __version__ from release.json
with (paths['source'] / 'release.json').open() as _release_file:
    release = json.load(_release_file, object_pairs_hook=AttrDict)
    __version__ = release.version

_sys_path = list(sys.path)      # Preserve original sys.path


def init(**kwargs):
    # Initialise configuration layers with provided paths
    paths.update(kwargs)
    for name, path in paths.items():
        if name not in config_layers:
            config_layers[name] = PathConfig(path / 'gramex.yaml')

    # Add imported folders to sys.path
    syspaths = set()
    for path_config in config_layers.values():
        for imp in path_config.__info__.imports:
            syspaths.add(str(imp.path.absolute().parent))
    sys.path[:] = _sys_path + list(syspaths)

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
