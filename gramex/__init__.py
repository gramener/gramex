'''Parses command line / configuration and runs Gramex.

Running `gramex` on the command line calls:

1. [gramex.commandline][] to parse command line arguments
2. [gramex.init][] to parse the configuration and start Gramex

This module also has

- [gramex.shutdown][] to shut down Gramex (e.g. on `Ctrl+C`)
- [gramex.gramex_update][] to check if Gramex is out of date
- [gramex.log][] to log messages persistently (e.g. on ElasticSearch)
'''

import os
import sys
import json
import yaml
import logging
import logging.config
from packaging import version
from pathlib import Path
from typing import List
from orderedattrdict import AttrDict
from gramex.config import ChainConfig, PathConfig, app_log, variables, setup_variables
from gramex.config import ioloop_running, prune_keys, setup_secrets

help = '''
Gramex {__version__} Copyright (c) 2017 by Gramener
Help: https://gramener.com/gramex/guide/

Common startup options

--listen.port=9090            Starts Gramex at port 9090
--log.level=warning           Accepts debug|info|warning|error|critical
--browser=true                Open the browser after startup
--settings.debug              Start Python debugger on error

Helper applications. For usage, run "gramex <app> --help"

gramex init                   Add Gramex project scaffolding to current dir
gramex service                Windows service setup
gramex mail                   Send email from command line
gramex license                See Gramex license, accept or reject it

Installation commands. For usage, run "gramex <command> --help"

gramex install                Install an app
gramex update                 Update an app
gramex setup                  Run make, npm install, bower install etc on app
gramex run                    Run an installed app
gramex uninstall              Uninstall an app
'''

__version__ = '1.86.0'

paths = AttrDict()  # Paths where configurations are stored
conf = AttrDict()  # Final merged configurations
config_layers = ChainConfig()  # Loads all configurations. init() updates it
appconfig = AttrDict()  # Final app configuration

paths['source'] = Path(__file__).absolute().parent  # Where gramex source code is
paths['base'] = Path('.')  # Where gramex is run from

callbacks = {}  # Services callbacks
_sys_path = list(sys.path)  # Preserve original sys.path


# List of URLs to warn about in case of duplicates
PathConfig.duplicate_warn = [
    'url.*',
    'cache.*',
    'schedule.*',
    'watch.*',
    'email.*',
    'alert.*',
    'sms.*',
    'log.loggers.*',
    'log.handlers.*',
    'log.formatters.*',
]


def commandline(args: List[str] = None):
    '''Run Gramex from the command line.

    Parameters:
        args: Command line arguments. If not provided, uses `sys.argv`

    Gramex can be run in 2 ways, both of which call [gramex.commandline][]:

    1. `python -m gramex`, which runs `__main__.py`.
    2. `gramex`, which runs `console_scripts` in `setup.py`

    `gramex -V` and `gramex --version` exit after printing the Gramex version.

    The positional arguments call different functions:

    - `gramex` runs Gramex and calls [gramex.init][]
    - `gramex init` creates a new Gramex project and calls [gramex.install.init][]
    - `gramex service` creates a Windows service and calls [gramex.install.service][]
    - ... etc. (Run `gramex help` for more)

    Keyword arguments are passed to the function, e.g.
    `gramex service install --startup=auto` calls
    `gramex.install.service('install', startup='auto')`.

    Keyword arguments with '.' are split into sub-keys, e.g.
    `gramex --listen.port 80` becomes `init(listen={"port": 80})`.

    Values are parsed as YAML, e.g. `null` becomes `None`.

    If the keyword arguments include `--help`, it prints the usage of that function and exits.
    '''
    commands = sys.argv[1:] if args is None else args

    # t first, setup log: service at INFO to log progress. App's log: may override this later.
    log_config = (+PathConfig(paths['source'] / 'gramex.yaml')).get('log', AttrDict())
    log_config.loggers.gramex.level = logging.INFO
    from . import services

    services.log(log_config)

    # kwargs has all optional command line args as a dict of values / lists.
    # args has all positional arguments as a list.
    kwargs = parse_command_line(commands)
    args = kwargs.pop('_')

    # If -V or --version is specified, print a message and end
    if 'V' in kwargs or 'version' in kwargs:
        pyver = '{0}.{1}.{2}'.format(*sys.version_info[:3])
        msg = [
            f'Gramex version: {__version__}',
            f'Gramex path: {paths["source"]}',
            f'Python version: {pyver}',
            f'Python path: {sys.executable}',
        ]
        return console(msg='\n'.join(msg))

    # Any positional argument is treated as a gramex command
    if len(args) > 0:
        base_command = args.pop(0).lower()
        method = 'install' if base_command == 'update' else base_command
        if method in {
            'install',
            'uninstall',
            'setup',
            'run',
            'service',
            'init',
            'mail',
            'license',
        }:
            import gramex.install

            if 'help' in kwargs:
                return console(msg=gramex.install.show_usage(method))
            return getattr(gramex.install, method)(args=args, kwargs=kwargs)
        raise NotImplementedError(f'Unknown gramex command: {base_command}')
    elif 'help' in kwargs:
        return console(msg=help.strip().format(**globals()))

    # Use current dir as base (where gramex is run from) if there's a gramex.yaml.
    if not os.path.isfile('gramex.yaml'):
        return console(msg='No gramex.yaml. See https://gramener.com/gramex/guide/')

    pyver = sys.version.replace('\n', ' ')
    app_log.info(f'Gramex {__version__} | {os.getcwd()} | Python {pyver}')

    # Run gramex.init(cmd={command line arguments like YAML variables})
    # --log.* settings are moved to log.loggers.gramex.*
    #   E.g. --log.level => log.loggers.gramex.level
    # --* remaining settings are moved to app.*
    #   E.g. --watch => app.watch
    config = AttrDict(app=kwargs)
    if kwargs.get('log'):
        config.log = AttrDict(loggers=AttrDict(gramex=kwargs.pop('log')))
        if 'level' in config.log.loggers.gramex:
            config.log.loggers.gramex.level = config.log.loggers.gramex.level.upper()
    return init(cmd=config)


def parse_command_line(commands: List[str]):
    # Parse command line arguments.
    # e.g. gramex cmd1 cmd2 --a=1 2 -b x --c --p.q=4
    # returns {"_": ["cmd1", "cmd2"], "a": [1, 2], "b": "x", "c": True, "p": {"q": [4]}}
    group = '_'
    args = AttrDict({group: []})
    for arg in commands:
        # If it's a keyword argument, extract key=value. "--key" becomes key=True
        if arg.startswith('-'):
            group, value = arg.lstrip('-'), 'True'
            if '=' in group:
                group, value = group.split('=', 1)
        # If it's a positional argument, leave the key as '_', and get the value
        else:
            value = arg

        # Parse values as YAML, e.g. null -> None
        value = yaml.safe_load(value)
        # If there are sub-keys, create a dict for them
        base = args
        keys = group.split('.')
        for key in keys[:-1]:
            base = base.setdefault(key, AttrDict())

        # Make a list where required. `--x=1 --x=2` becomes {x: [1, 2]}
        # If key is present, make it a list.
        # If key is a list, append to it.
        if keys[-1] not in base or base[keys[-1]] is True:
            base[keys[-1]] = value
        elif not isinstance(base[keys[-1]], list):
            base[keys[-1]] = [base[keys[-1]], value]
        else:
            base[keys[-1]].append(value)

    return args


def init(force_reload: bool = False, **kwargs) -> None:
    '''Load Gramex configurations and start / restart the Gramex instance.

    Parameters:
        force_reload (bool): Reload services even config hasn't changed
        **kwargs (dict): Overrides config

    `gramex.init()` loads configurations from 3 sources, which override each other:

    1. Gramex's `gramex.yaml`
    2. Current directory's `gramex.yaml`
    3. The `kwargs`

    Then it calls each [gramex.services][] with its configuration.

    It can be called multiple times. For efficiency, a services function is called only if its
    configuration has changed or `force_reload=True`.

    If a kwarg value is:

    - a string, it's loaded as-is
    - a Path pointing to a file, it's loaded as a YAML config file
    - a Path pointing to a directory, it loads a `gramex.yaml` file from that directory
    '''
    # Set up secrets from .secrets.yaml, if any
    try:
        setup_secrets(paths['base'] / '.secrets.yaml')
    except Exception as e:
        app_log.exception(e)

    # Add base path locations where config files are found to sys.path.
    # This allows variables: to import files from folder where configs are defined.
    sys.path[:] = _sys_path + [
        str(path.absolute()) for path in paths.values() if isinstance(path, Path)
    ]

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

    globals()['service'] = services.info  # gramex.service = gramex.services.info

    # Override final configurations
    appconfig.clear()
    appconfig.update(+config_layers)
    # If --settings.debug, override root and Gramex loggers to show debug messages
    if appconfig.app.get('settings', {}).get('debug', False):
        appconfig.log.root.level = appconfig.log.loggers.gramex.level = logging.DEBUG

    # Set up a watch on config files (including imported files)
    if appconfig.app.get('watch', True):
        from services import watcher

        watcher.watch('gramex-reconfig', paths=config_files, on_modified=lambda event: init())

    # Run all valid services. (The "+" before config_chain merges the chain)
    # Services may return callbacks to be run at the end
    for key, val in appconfig.items():
        if key not in conf or conf[key] != val or force_reload:
            if hasattr(services, key):
                app_log.debug(f'Loading service: {key}')
                conf[key] = prune_keys(val, {'comment'})
                callback = getattr(services, key)(conf[key])
                if callable(callback):
                    callbacks[key] = callback
            else:
                app_log.error(f'No service named {key}')

    # Run the callbacks. Specifically, the app service starts the Tornado ioloop
    for key in (+config_layers).keys():
        if key in callbacks:
            app_log.debug(f'Running callback: {key}')
            callbacks[key]()


def shutdown():
    '''Shut down the running Gramex instance.'''
    from . import services

    ioloop = services.info.main_ioloop
    if ioloop_running(ioloop):
        app_log.info('Shutting down Gramex...')
        # Shut down Gramex in a thread-safe way. add_callback is the ONLY thread-safe method
        ioloop.add_callback(ioloop.stop)


def gramex_update(url: str):
    '''Check if a newer version of Gramex is available. If yes, log a warning.

    Parameters:
        url: URL to check for new version

    Gramex uses <https://gramener.com/gramex-update/> as the URL to check for new versions.
    '''
    import time
    import requests
    import platform
    from . import services

    if not services.info.eventlog:
        return app_log.error('eventlog: service is not running. So Gramex update is disabled')

    query = services.info.eventlog.query
    update = query('SELECT * FROM events WHERE event="update" ORDER BY time DESC LIMIT 1')
    delay = 24 * 60 * 60  # Wait for one day before updates
    if update and time.time() < update[0]['time'] + delay:
        return app_log.debug('Gramex update ran recently. Deferring check.')

    meta = {
        'dir': variables.get('GRAMEXDATA'),
        'uname': platform.uname(),
    }
    if update:
        events = query('SELECT * FROM events WHERE time > ? ORDER BY time', (update[0]['time'],))
    else:
        events = query('SELECT * FROM events')
    logs = [dict(log, **meta) for log in events]

    r = requests.post(url, data=json.dumps(logs))
    r.raise_for_status()
    update = r.json()
    server_version = update['version']
    if version.parse(server_version) > version.parse(__version__):
        app_log.error(f'Gramex {server_version} is available. https://gramener.com/gramex/guide/')
    elif version.parse(server_version) < version.parse(__version__):
        app_log.warning(f'Gramex {__version__} is ahead of stable {server_version}')
    else:
        app_log.debug(f'Gramex {__version__} is up to date')
    services.info.eventlog.add('update', update)
    return {'logs': logs, 'response': update}


def log(*args, **kwargs):
    '''Logs structured information for future reference.

    Examples:
        >>> gramex.log(level='INFO', x=1, msg='abc')

        This logs `{level: INFO, x: 1, msg: abc}` into a logging queue.

        If a `gramexlog` service like ElasticSearch has been configured, it will periodically flush
        the logs into the server.
    '''
    from . import services

    # gramexlog() positional arguments may have a handler and app (in any order)
    # The app defaults to the first gramexlog:
    handler, app = None, services.info.gramexlog.get('defaultapp', None)
    for arg in args:
        # Pretend that anything that has a .args is a handler
        if hasattr(getattr(arg, 'args', None), 'items'):
            handler = arg
        # ... and anything that's a string is an index name. The last string overrides all
        elif isinstance(arg, str):
            app = arg
    # If the user logs into an unknown app, stop immediately
    try:
        conf = services.info.gramexlog.apps[app]
    except KeyError:
        raise ValueError(f'gramexlog: no config for {app}')

    # Add all URL query parameters. In case of multiple values, capture the last
    if handler:
        kwargs.update({key: val[-1] for key, val in handler.args.items()})
    # Add additional keys specified in gramex.yaml via keys:
    kwargs.update(conf.extra_keys(handler))
    conf.queue.append(kwargs)


def console(msg):
    '''Write message to console. An alias for print().'''
    print(msg)  # noqa
