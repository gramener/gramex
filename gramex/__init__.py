import os
import sys
import json
import yaml
import logging
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
    # Else use source/guide, and point the user to the welcome screen
    if not os.path.isfile('gramex.yaml'):
        os.chdir(str(paths['source'] / 'guide'))
        paths['base'] = Path('.')
        if 'browser' not in cmd:
            cmd['browser'] = '/welcome'

    # Initialize Gramex in the current dir, and command line args as config layers
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

    # Locate all config files
    config_files = set()
    for path_config in config_layers.values():
        if hasattr(path_config, '__info__'):
            for pathinfo in path_config.__info__.imports:
                config_files.add(pathinfo.path)
    config_files = list(config_files)

    # Add config file folders to sys.path
    sys.path[:] = _sys_path + [str(path.absolute().parent) for path in config_files]

    # Set up a watch on config files (including imported files)
    from . import services      # noqa -- deferred import for optimisation
    services.watcher.watch('gramex-reconfig', paths=config_files, on_modified=lambda event: init())

    # Run all valid services. (The "+" before config_chain merges the chain)
    # Services may return callbacks to be run at the end
    callbacks = []
    for key, val in (+config_layers).items():
        if key not in conf or conf[key] != val:
            if hasattr(services, key):
                conf[key] = deepcopy(val)
                callback = getattr(services, key)(conf[key])
                if callable(callback):
                    callbacks.append(callback)
            else:
                logging.warning('No service named %s', key)

    # Run the callbacks. Specifically, the app service starts the Tornado ioloop
    for callback in callbacks:
        callback()


def shutdown():
    'Shut down this instance'
    ioloop = tornado.ioloop.IOLoop.current()
    if ioloop._running:
        logging.info('Shutting down Gramex...')
        ioloop.stop()
