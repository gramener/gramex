import os
import sys
import json
import yaml
import logging
import webbrowser
import tornado.ioloop
from pathlib import Path
from copy import deepcopy
from orderedattrdict import AttrDict
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


# Entry Points
# ------------
# There are 2 entry points into Gramex: commandline() and init().
# commandline() will be called by python -m gramex, gramex.exe, etc.
# init() will be called after import gramex -- when using Gramex as a library.

def commandline(**kwargs):
    'Run Gramex from the command line'
    # Set logging level to info at startup. (Services may override logging level.)
    # This ensures that startup info is printed when Gramex is run the first time.
    logging.basicConfig(level=logging.INFO)
    logging.info('Initializing Gramex...')

    # Parse command line arguments.
    # --listen.port=8080 => {'listen': {'port': 8080}}
    cmd = AttrDict()
    for arg in sys.argv[1:]:
        if arg.startswith('--') and '=' in arg:
            name, value = arg[2:].split('=', 1)
            keys = name.split('.')
            base = cmd
            for key in keys[:-1]:
                base = base.setdefault(key, AttrDict())
            base[keys[-1]] = yaml.load(value)

    # Use current dir as base (where gramex is run from) if there's a gramex.yaml.
    # Else use source/help
    if not os.path.isfile('gramex.yaml'):
        paths['base'] = paths['source'] / 'help'

    # Initialize Gramex, adding command line arguments as a config layer
    init(cmd=AttrDict(app=cmd))


def init(**kwargs):
    '''
    Update Gramex configurations and start / restart the instance.

    ``gramex.init()`` can be called any time to refresh configuration files.

    ``gramex.init(key=val)`` adds ``val`` as a configuration layer named
    ``key``. The next time ``gramex.init(key=...)`` is called, the key is
    ignored. But every time ``gramex.init(...)`` is called subsequently, the
    ``val`` is re-evaluated and stored in ``gramex.conf``.
    '''
    # Initialise configuration layers with provided configurations
    paths.update(kwargs)
    for key, val in paths.items():
        if key not in config_layers:
            config_layers[key] = PathConfig(val / 'gramex.yaml') if isinstance(val, Path) else val

    # Add imported folders to sys.path
    syspaths = set()
    for path_config in config_layers.values():
        if hasattr(path_config, '__info__'):
            for imp in path_config.__info__.imports:
                syspaths.add(str(imp.path.absolute().parent))
    sys.path[:] = _sys_path + list(syspaths)

    # Run all valid services. (The "+" before config_chain merges the chain)
    from . import services      # noqa -- deferred import for optimisation
    for key, val in (+config_layers).items():
        if key not in conf or conf[key] != val:
            if hasattr(services, key):
                conf[key] = deepcopy(val)
                getattr(services, key)(conf[key])
            else:
                logging.warning('No service named %s', key)

    # Switch to the base folder
    os.chdir(str(paths['base']))

    # Start the IOLoop. TODO: can the app service start this delayed?
    ioloop = tornado.ioloop.IOLoop.current()
    if not ioloop._running:
        logging.info('Listening on port %d', conf.app.listen.port)
        if conf.app.browser:
            url = 'http://127.0.0.1:%d/' % conf.app.listen.port
            browser = webbrowser.get()
            logging.info('Opening %s in %s browser', url, browser.__class__.__name__)
            browser.open(url)
        ioloop.start()


def shutdown():
    'Shut down this instance'
    ioloop = tornado.ioloop.IOLoop.current()
    if ioloop._running:
        logging.info('Shutting down Gramex...')
        ioloop.stop()
