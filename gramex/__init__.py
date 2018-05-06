'''
Gramex {__version__} Copyright (C) 2017 by Gramener

Start the Gramex server on port 9988 at the current directory.
If no gramex.yaml exists, show the guide (https://learn.gramener.com/guide/)

Options
  --listen.port=9090            Starts Gramex at port 9090
  --browser                     Open the browser after startup
  --settings.debug              Enable serving tracebacks and autoreload
  --settings.xsrf_cookies=false Disable XSRF cookies (only for testing)
  --settings.cookie_secret=...  Change cookie encryption key

Helper applications
  gramex init                   Add Gramex project scaffolding to current dir
  gramex service                Windows service setup
  gramex mail                   Send email from command line

Installation commands. Run without arguments to see help
  gramex install                Install an app
  gramex update                 Update an app
  gramex setup                  Run make, npm install, bower install etc on app
  gramex run                    Run an installed app
  gramex uninstall              Uninstall an app
'''

import os
import sys
import json
import yaml
import logging
import logging.config
import tornado.ioloop
from pathlib import Path
from copy import deepcopy
from orderedattrdict import AttrDict
from gramex.config import ChainConfig, PathConfig, app_log, variables, setup_variables
from gramex.config import ioloop_running

paths = AttrDict()              # Paths where configurations are stored
conf = AttrDict()               # Final merged configurations
config_layers = ChainConfig()   # Loads all configurations. init() updates it

paths['source'] = Path(__file__).absolute().parent      # Where gramex source code is
paths['base'] = Path('.')                               # Where gramex is run from

callbacks = {}                  # Services callbacks

# Populate __version__ from release.json
with (paths['source'] / 'release.json').open() as _release_file:
    release = json.load(_release_file, object_pairs_hook=AttrDict)
    __version__ = release.version

_sys_path = list(sys.path)      # Preserve original sys.path


# List of URLs to warn about in case of duplicates
PathConfig.duplicate_warn = [
    'url.*',
    'cache.*',
    'schedule.*',
    'watch.*',
    'email.*',
    'alert.*',
    'sms.*',
    'log.loggers.*', 'log.handlers.*', 'log.formatters.*',
]


def parse_command_line(commands):
    '''
    Parse command line arguments. For example:

        gramex cmd1 cmd2 --a=1 2 -b x --c --p.q=4

    returns:

        {"_": ["cmd1", "cmd2"], "a": [1, 2], "b": "x", "c": True, "p": {"q": [4]}}

    Values are parsed as YAML. Arguments with '.' are split into subgroups. For
    example, ``gramex --listen.port 80`` returns ``{"listen": {"port": 80}}``.
    '''
    group = '_'
    args = AttrDict({group: []})
    for arg in commands:
        if arg.startswith('-'):
            group, value = arg.lstrip('-'), 'True'
            if '=' in group:
                group, value = group.split('=', 1)
        else:
            value = arg

        value = yaml.safe_load(value)
        base = args
        keys = group.split('.')
        for key in keys[:-1]:
            base = base.setdefault(key, AttrDict())

        # Add the key to the base.
        # If it's already there, make it a list.
        # If it's already a list, append to it.
        if keys[-1] not in base or base[keys[-1]] is True:
            base[keys[-1]] = value
        elif not isinstance(base[keys[-1]], list):
            base[keys[-1]] = [base[keys[-1]], value]
        else:
            base[keys[-1]].append(value)

    return args


def callback_commandline(commands):
    '''
    Find what method should be run based on the command line programs. This
    refactoring allows us to test gramex.commandline() to see if it processes
    the command line correctly, without actually running the commands.

    Returns a callback method and kwargs for the callback method.
    '''
    # Ensure that log colours are printed properly on cygwin.
    if sys.platform == 'cygwin':        # colorama.init() gets it wrong on Cygwin
        import colorlog.escape_codes    # noqa: Let colorlog call colorama.init() first
        import colorama
        colorama.init(convert=True)     # Now we'll override with convert=True

    # Set logging config at startup. (Services may override this.)
    log_config = (+PathConfig(paths['source'] / 'gramex.yaml')).get('log', AttrDict())
    log_config.root.level = logging.INFO
    from . import services
    services.log(log_config)

    # args has all optional command line args as a dict of values / lists.
    # cmd has all positional arguments as a list.
    args = parse_command_line(commands)
    cmd = args.pop('_')

    # If --help or -V --version is specified, print a message and end
    if args.get('V') is True or args.get('version') is True:
        return console, {'msg': 'Gramex %s' % __version__}
    if args.get('help') is True:
        return console, {'msg': __doc__.strip().format(**globals())}

    # Any positional argument is treated as a gramex command
    if len(cmd) > 0:
        kwargs = {'cmd': cmd, 'args': args}
        base_command = cmd.pop(0).lower()
        method = 'install' if base_command == 'update' else base_command
        if method in {'install', 'uninstall', 'setup', 'run', 'service', 'init', 'mail'}:
            import gramex.install
            return getattr(gramex.install, method), kwargs
        raise NotImplementedError('Unknown gramex command: %s' % base_command)

    # Use current dir as base (where gramex is run from) if there's a gramex.yaml.
    # Else use source/guide, and point the user to the welcome screen
    if not os.path.isfile('gramex.yaml'):
        from gramex.install import run
        args.setdefault('browser', '/welcome')
        return run, {'cmd': ['guide'], 'args': args}

    app_log.info('Gramex %s | %s | Python %s', __version__, os.getcwd(),
                 sys.version.replace('\n', ' '))
    return init, {'cmd': AttrDict(app=args)}


def commandline(args=None):
    '''
    Run Gramex from the command line. Called via:

    - setup.py console_scripts when running gramex
    - __main__.py when running python -m gramex
    '''
    callback, kwargs = callback_commandline(sys.argv[1:] if args is None else args)
    callback(**kwargs)


def gramex_update(url):
    '''If a newer version of gramex is available, logs a warning'''
    import time
    import requests
    import platform
    from . import services

    if not services.info.eventlog:
        return app_log.error('eventlog: service is not running. So Gramex update is disabled')
    conn = services.info.eventlog.conn
    query = 'SELECT * FROM events WHERE event="update" ORDER BY time DESC LIMIT 1'
    update = conn.execute(query).fetchone()
    delay = 24 * 60 * 60            # Wait for one day before updates
    if update is not None and time.time() < update['time'] + delay:
        return app_log.debug('Gramex update ran recently. Deferring check.')

    meta = {
        'dir': variables.get('GRAMEXDATA'),
        'uname': platform.uname(),
    }
    if update is None:
        events = conn.execute('SELECT * FROM events')
    else:
        events = conn.execute('SELECT * FROM events WHERE time > ? ORDER BY time',
                              (update['time'], ))
    logs = [dict(log, **meta) for log in events]

    r = requests.post(url, data=json.dumps(logs))
    r.raise_for_status()
    update = r.json()
    version = update['version']
    if version > __version__:
        app_log.error('Gramex %s is available. See https://learn.gramener.com/guide/', version)
    elif version < __version__:
        app_log.warning('Gramex update: your version %s is ahead of the stable %s',
                        __version__, version)
    else:
        app_log.debug('Gramex version %s is up to date', __version__)
    services.info.eventlog.add('update', update)
    return {'logs': logs, 'response': update}


def console(msg):
    '''Write message to console'''
    print(msg)              # noqa


def init(force_reload=False, **kwargs):
    '''
    Update Gramex configurations and start / restart the instance.

    ``gramex.init()`` can be called any time to refresh configuration files.
    ``gramex.init(key=val)`` adds ``val`` as a configuration layer named
    ``key``. If ``val`` is a Path, it is converted into a PathConfig. (If it is
    Path directory, use ``gramex.yaml``.)

    Services are re-initialised if their configurations have changed. Service
    callbacks are always re-run (even if the configuration hasn't changed.)
    '''
    # Reset variables
    variables.clear()
    variables.update(setup_variables())

    # Initialise configuration layers with provided configurations
    # AttrDicts are updated as-is. Paths are converted to PathConfig
    paths.update(kwargs)
    for key, val in paths.items():
        if isinstance(val, Path):
            if val.is_dir():
                val = val / 'gramex.yaml'
            val = PathConfig(val)
        config_layers[key] = val

    # Locate all config files
    config_files = set()
    for path_config in config_layers.values():
        if hasattr(path_config, '__info__'):
            for pathinfo in path_config.__info__.imports:
                config_files.add(pathinfo.path)
    config_files = list(config_files)

    # Add config file folders to sys.path
    sys.path[:] = _sys_path + [str(path.absolute().parent) for path in config_files]

    from . import services
    globals()['service'] = services.info    # gramex.service = gramex.services.info

    # Set up a watch on config files (including imported files)
    from services import watcher
    watcher.watch('gramex-reconfig', paths=config_files, on_modified=lambda event: init())

    # Override final configurations
    final_config = +config_layers
    # --settings.debug => log.root.level = True
    if final_config.app.get('settings', {}).get('debug', False):
        final_config.log.root.level = logging.DEBUG

    # Run all valid services. (The "+" before config_chain merges the chain)
    # Services may return callbacks to be run at the end
    for key, val in final_config.items():
        if key not in conf or conf[key] != val or force_reload:
            if hasattr(services, key):
                app_log.debug('Loading service: %s', key)
                conf[key] = deepcopy(val)
                callback = getattr(services, key)(conf[key])
                if callable(callback):
                    callbacks[key] = callback
            else:
                app_log.error('No service named %s', key)

    # Run the callbacks. Specifically, the app service starts the Tornado ioloop
    for key in (+config_layers).keys():
        if key in callbacks:
            app_log.debug('Running callback: %s', key)
            callbacks[key]()


def shutdown():
    '''Shut down this instance'''
    ioloop = tornado.ioloop.IOLoop.current()
    if ioloop_running(ioloop):
        app_log.info('Shutting down Gramex...')
        ioloop.stop()
