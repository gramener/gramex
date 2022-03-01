'''
Gramex {__version__} Copyright (c) 2017 by Gramener
Help: https://gramener.com/gramex/guide/

Common startup options
  --listen.port=9090            Starts Gramex at port 9090
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

import os
import sys
import json
import yaml
import logging
import logging.config
from packaging import version
from pathlib import Path
from orderedattrdict import AttrDict
from gramex.config import ChainConfig, PathConfig, app_log, variables, setup_variables
from gramex.config import ioloop_running, prune_keys, setup_secrets

paths = AttrDict()              # Paths where configurations are stored
conf = AttrDict()               # Final merged configurations
config_layers = ChainConfig()   # Loads all configurations. init() updates it
appconfig = AttrDict()          # Final app configuration

paths['source'] = Path(__file__).absolute().parent      # Where gramex source code is
paths['base'] = Path('.')                               # Where gramex is run from

callbacks = {}                  # Services callbacks

# Populate __version__ from release.json
with (paths['source'] / 'release.json').open() as _release_file:
    release = json.load(_release_file, object_pairs_hook=AttrDict)
    __version__ = release.info.version

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
    # Set logging config at startup. (Services may override this.)
    log_config = (+PathConfig(paths['source'] / 'gramex.yaml')).get('log', AttrDict())
    log_config.root.level = logging.INFO
    from . import services
    services.log(log_config)

    # kwargs has all optional command line args as a dict of values / lists.
    # args has all positional arguments as a list.
    kwargs = parse_command_line(commands)
    args = kwargs.pop('_')

    # If --help or -V --version is specified, print a message and end
    if kwargs.get('V') is True or kwargs.get('version') is True:
        pyver = '{0}.{1}.{2}'.format(*sys.version_info[:3])
        msg = [
            f'Gramex version: {__version__}',
            f'Gramex path: {paths["source"]}',
            f'Python version: {pyver}',
            f'Python path: {sys.executable}',
        ]
        return console, {'msg': '\n'.join(msg)}

    # Any positional argument is treated as a gramex command
    if len(args) > 0:
        base_command = args.pop(0).lower()
        method = 'install' if base_command == 'update' else base_command
        if method in {
            'install', 'uninstall', 'setup', 'run', 'service', 'init',
            'mail', 'license',
        }:
            import gramex.install
            if 'help' in kwargs:
                return console, {'msg': gramex.install.show_usage(method)}
            return getattr(gramex.install, method), {'args': args, 'kwargs': kwargs}
        raise NotImplementedError(f'Unknown gramex command: {base_command}')
    elif kwargs.get('help') is True:
        return console, {'msg': __doc__.strip().format(**globals())}

    # Use current dir as base (where gramex is run from) if there's a gramex.yaml.
    if not os.path.isfile('gramex.yaml'):
        return console, {'msg': 'No gramex.yaml. See https://gramener.com/gramex/guide/'}

    # Run gramex.init(cmd={command line arguments like YAML variables})
    pyver = sys.version.replace('\n', ' ')
    app_log.info(f'Gramex {__version__} | {os.getcwd()} | Python {pyver}')
    return init, {'cmd': AttrDict(app=kwargs)}


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

    query = services.info.eventlog.query
    update = query('SELECT * FROM events WHERE event="update" ORDER BY time DESC LIMIT 1')
    delay = 24 * 60 * 60            # Wait for one day before updates
    if update and time.time() < update[0]['time'] + delay:
        return app_log.debug('Gramex update ran recently. Deferring check.')

    meta = {
        'dir': variables.get('GRAMEXDATA'),
        'uname': platform.uname(),
    }
    if update:
        events = query('SELECT * FROM events WHERE time > ? ORDER BY time',
                       (update[0]['time'], ))
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
    try:
        setup_secrets(paths['base'] / '.secrets.yaml')
    except Exception as e:
        app_log.exception(e)

    # Add base path locations where config files are found to sys.path.
    # This allows variables: to import files from folder where configs are defined.
    sys.path[:] = _sys_path + [
        str(path.absolute()) for path in paths.values()
        if isinstance(path, Path)
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
    globals()['service'] = services.info    # gramex.service = gramex.services.info

    # Override final configurations
    appconfig.clear()
    appconfig.update(+config_layers)
    # --settings.debug => log.root.level = True
    if appconfig.app.get('settings', {}).get('debug', False):
        appconfig.log.root.level = logging.DEBUG

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
    '''Shut down this instance'''
    from . import services
    ioloop = services.info.main_ioloop
    if ioloop_running(ioloop):
        app_log.info('Shutting down Gramex...')
        # Shut down Gramex in a thread-safe way. add_callback is the ONLY thread-safe method
        ioloop.add_callback(ioloop.stop)


def log(*args, **kwargs):
    '''
    Logs structured information for future reference. Typical usage::

        gramex.log(level='INFO', x=1, msg='abc')

    This logs ``{level: INFO, x: 1, msg: abc}`` into a logging queue. If a `gramexlog` service like
    ElasticSearch has been configured, it will periodically flush the logs into the server.
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
