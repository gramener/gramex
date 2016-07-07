'''
# This docstring is in YAML, and is used by the usage variable.
# It documents the help for the Gramex command line commands supported.

install: |
    usage:
        gramex install <app> <url> [--target=DIR]
        gramex install <app> --cmd="COMMAND" [--target=DIR]

    "app" is any name you want to locally call the application.

    "url" can be a:
        - local ZIP file (/path/to/app.zip)
        - local directory (/path/to/directory)
        - URL of a ZIP file (https://github.com/user/repo/archive/master.zip)

    target is the directory to install at (defaults to user data directory.)

    cmd is a shell command to run. If it has the word "TARGET" in caps, it is
    replaced by the target directory.

    After installation, Gramex runs the following commands if possible:
        - make
        - powershell -File setup.ps1
        - bash setup.sh
        - python setup.py
        - npm install
        - bower install

    Installed apps:
    {apps}

run: |
    usage: gramex run <app> [--target=DIR] [--dir=DIR] [--<options>=<value>]

    "app" is the name of the locally installed application.

    If "app" is not installed, specify --target=DIR to run from DIR. The next
    "gramex run app" will automatically run from DIR.

    "dir" is a *sub-directory* under "target" to run from. This is useful if
    "app" has multiple sub-applications.

    All Gramex command line options can be used. These are saved. For example:

        gramex run app --target=/path/to/dir --listen.port=8899 --browser=true

    ... will preserve the "target", "listen.port" and "browser" values. Running
    "gramex run app" will re-use these values. To clear the option, leave the
    value blank. For example "--browser=" will clear the browser option.

    Installed apps:
    {apps}

uninstall: |
    usage: gramex uninstall <app> [<app> ...]

    "app" is the name of the locally installed application. You can uninstall
    multiple applications in one command.

    All information about the application is lost. You cannot undo this.

    Installed apps:
    {apps}
'''

import os
import six
import sys
import yaml
import stat
import shlex
import shutil
import string
import datetime
import requests
from shutilwhich import which
from pathlib import Path
from subprocess import Popen
from orderedattrdict import AttrDict
from zipfile import ZipFile
import gramex
from gramex.config import ChainConfig, PathConfig, variables, app_log

usage = yaml.load(__doc__)


def _ensure_remove(remove, path, exc_info):
    '''onerror callback for rmtree that tries hard to delete files'''
    if issubclass(exc_info[0], WindowsError):
        import winerror
        # Delete read-only files on Windows
        # https://bugs.python.org/issue19643
        # https://bugs.python.org/msg218021
        if exc_info[1].winerror == winerror.ERROR_ACCESS_DENIED:
            os.chmod(path, stat.S_IWRITE)
            return remove(path)
        # Delay delete a bit if directory is used by another process.
        # Typically happens on uninstall immediately after bower / npm / git
        # (e.g. during testing.)
        if exc_info[1].winerror == winerror.ERROR_SHARING_VIOLATION:
            import time
            delays = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
            for delay in delays:
                time.sleep(delay)
                try:
                    return remove(path)
                except WindowsError:
                    pass
    raise exc_info[1]


def safe_rmtree(target):
    if not os.path.exists(target):
        return True
    elif target.startswith(variables['GRAMEXDATA']):
        shutil.rmtree(target, onerror=_ensure_remove)
        return True
    else:
        app_log.warn('Not removing directory %s (outside $GRAMEXDATA)', target)
        return False


def zip_prefix_filter(members, prefix):
    '''
    Return only ZIP file members starting with the directory prefix, with the
    prefix stripped out.
    '''
    if not prefix:
        return members
    offset = len(prefix)
    result = []
    for zipinfo in members:
        if zipinfo.filename.startswith(prefix):
            zipinfo.filename = zipinfo.filename[offset:]
            if len(zipinfo.filename) > 0:
                result.append(zipinfo)
    return result


def download_zip(config):
    '''
    Download config.url into config.target.
    If config.url is a directory, copy it.
    If config.url is a file or a URL (http, https, ftp), unzip it.
    If config.contentdir is True, skip parent folders with single subfolder.
    If no files match, log a warning.
    '''
    url, target = config.url, config.target

    # If the URL is a directory, copy it
    if os.path.isdir(url):
        if os.path.exists(target):
            url = os.path.abspath(url).lower().strip(os.sep)
            target = os.path.abspath(target).lower().strip(os.sep)
            if url != target:
                if not safe_rmtree(target):
                    return
        if url != target:
            shutil.copytree(url, target)
            app_log.info('Copied %s into %s', url, target)
        config.url = url
        return

    # If it's a file, unzip it
    if os.path.exists(url):
        handle = url
    else:
        # Otherwise, assume that it's a URL containing a ZIP file
        app_log.info('Downloading: %s', url)
        response = requests.get(url)
        response.raise_for_status()
        handle = six.BytesIO(response.content)

    # Identify relevant files from the ZIP file
    zipfile = ZipFile(handle)
    files = zipfile.infolist()
    if config.get('contentdir', True):
        prefix = os.path.commonprefix(zipfile.namelist())
        if prefix.endswith('/'):
            files = zip_prefix_filter(files, prefix)

    # Extract relevant files from ZIP file
    if safe_rmtree(target):
        zipfile.extractall(target, files)
        app_log.info('Extracted %d files into %s', len(files), target)


def run_command(config):
    '''
    Run config.cmd. If the command has a TARGET, replace it with config.target.
    Else append config.target as an argument.
    '''
    appcmd = config.cmd
    # Split the command into an array of words
    if isinstance(appcmd, six.string_types):
        appcmd = shlex.split(appcmd)
    # Replace TARGET with the actual target
    if 'TARGET' in appcmd:
        appcmd = [config.target if arg == 'TARGET' else arg for arg in appcmd]
    else:
        appcmd.append(config.target)
    app_log.info('Running %s', ' '.join(appcmd))
    if not safe_rmtree(config.target):
        return
    proc = Popen(appcmd, bufsize=-1, stdout=sys.stdout, stderr=sys.stderr)
    proc.communicate()


setup_paths = AttrDict((
    ('make', {'file': 'Makefile', 'cmd': '"$EXE"'}),
    ('powershell', {'file': 'setup.ps1', 'cmd': '"$EXE" -File "$FILE"'}),
    ('bash', {'file': 'setup.sh', 'cmd': '"$EXE" "$FILE"'}),
    ('pip', {'file': 'requirements.txt', 'cmd': '"$EXE" install --upgrade -r "$FILE"'}),
    ('python', {'file': 'setup.py', 'cmd': '"$EXE" "$FILE"'}),
    ('npm', {'file': 'package.json', 'cmd': '"$EXE" install'}),
    ('bower', {'file': 'bower.json', 'cmd': '"$EXE" install'}),
))


def run_setup(config):
    target = config.target
    for exe, setup in setup_paths.items():
        setup_file = os.path.join(target, setup['file'])
        if not os.path.exists(setup_file):
            continue
        exe_path = which(exe)
        if exe_path is None:
            app_log.info('Skipping %s. No %s found', setup_file, exe)
            continue
        cmd = string.Template(setup['cmd']).substitute(FILE=setup_file, EXE=exe_path)
        app_log.info('Running %s', cmd)
        proc = Popen(shlex.split(cmd), cwd=target, bufsize=-1,
                     stdout=sys.stdout, stderr=sys.stderr)
        proc.communicate()


app_dir = Path(variables.get('GRAMEXDATA')) / 'apps'
if not app_dir.exists():
    app_dir.mkdir(parents=True)

# Get app configuration by chaining apps.yaml in gramex + app_dir + command line
apps_config = ChainConfig()
apps_config['base'] = PathConfig(gramex.paths['source'] / 'apps.yaml')
user_config_file = app_dir / 'apps.yaml'
apps_config['user'] = PathConfig(user_config_file)

app_keys = {
    'url': 'URL / filename of a ZIP file to install',
    'cmd': 'Command used to install file',
    'dir': 'Sub-directory under "url" to run from (optional)',
    'contentdir': 'Strip root directory with a single child (optional, default=True)',
    'target': 'Local directory where the app is installed',
    'installed': 'Additional installation information about the app',
    'run': 'Runtime keyword arguments for the app',
}


def save_user_config(appname, value):
    user_config = AttrDict()
    if user_config_file.exists():
        with user_config_file.open(encoding='utf-8') as handle:
            user_config = yaml.load(handle)
    if value is None:
        if appname in user_config:
            del user_config[appname]
    else:
        app_config = user_config.setdefault(appname, AttrDict())
        app_config.update({key: value[key] for key in app_keys if key in value})

    with user_config_file.open(mode='w', encoding='utf-8') as handle:
        yaml.dump(user_config, handle, indent=4, default_flow_style=False)


def get_app_config(appname, args):
    '''
    Get the stored configuration for appname, and override it with args.
    ``.target`` defaults to $GRAMEXDATA/apps/<appname>.
    '''
    apps_config['cmd'] = {appname: args}
    app_config = (+apps_config).get(appname, {})
    app_config.setdefault('target', str(app_dir / app_config.get('target', appname)))
    app_config.target = os.path.abspath(app_config.target)
    return app_config


def flatten_config(config, base=None):
    'Get flattened configurations'
    for key, value in config.items():
        keystr = key if base is None else base + '.' + key
        if hasattr(value, 'items'):
            for sub in flatten_config(value, keystr):
                yield sub
        else:
            yield keystr, value


def show_usage(command):
    apps = (+apps_config).keys()
    return 'gramex {command}\n\n{desc}'.format(
        command=command,
        desc=usage[command].strip().format(
            apps='\n'.join('- ' + app for app in sorted(apps))
        ))


def install(cmd, args):
    if len(cmd) < 1:
        app_log.error(show_usage('install'))
        return

    appname = cmd[0]
    app_log.info('Installing: %s', appname)
    app_config = get_app_config(appname, args)
    if len(cmd) == 2:
        app_config.url = cmd[1]
        download_zip(app_config)
    elif 'url' in app_config:
        download_zip(app_config)
    elif 'cmd' in app_config:
        run_command(app_config)
    else:
        app_log.error('Use --url=... or --cmd=... to specific source of %s', appname)
        return

    # Post-installation
    run_setup(app_config)
    app_config['installed'] = {'time': datetime.datetime.utcnow()}
    save_user_config(appname, app_config)
    app_log.info('Installed. Run `gramex run %s`', appname)


def uninstall(cmd, args):
    if len(cmd) < 1:
        app_log.error(show_usage('uninstall'))
        return
    if len(cmd) > 1 and args:
        app_log.error('Arguments allowed only with single app. Ignoring %s', ', '.join(cmd[1:]))
        cmd = cmd[:1]

    for appname in cmd:
        app_log.info('Uninstalling: %s', appname)

        # Delete the target directory if it exists
        app_config = get_app_config(appname, args)
        if os.path.exists(app_config.target):
            safe_rmtree(app_config.target)
        else:
            app_log.error('No directory %s to remove', app_config.target)
        save_user_config(appname, None)


def run(cmd, args):
    if len(cmd) < 1:
        app_log.error(show_usage('run'))
        return
    if len(cmd) > 1:
        app_log.error('Can only run one app. Ignoring %s', ', '.join(cmd[1:]))

    appname = cmd.pop(0)
    app_config = get_app_config(appname, args)

    target = app_config.target
    if 'dir' in app_config:
        target = os.path.join(target, app_config.dir)
    if os.path.isdir(target):
        os.chdir(target)
        gramex.paths['base'] = Path('.')
        # If we run with updated parameters, save for next run under the .run config
        run_config = app_config.setdefault('run', {})
        for key, val in args.items():
            if key not in app_keys:
                run_config[key] = app_config.pop(key)
        save_user_config(appname, app_config)
        # Tell the user what configs are used
        app_log.info('Gramex %s | %s %s loading...', gramex.__version__, appname, ' '.join(
            ['--%s=%s' % arg for arg in flatten_config(app_config.get('run', {}))]))
        gramex.init(cmd=AttrDict(app=app_config['run']))
    else:
        app_log.error('%s: no directory %s', appname, app_config.target)
