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


def _rmtree_readonly(remove, path, exc_info):
    '''onerror callback for rmtree that deletes read-only files on Windows'''
    # https://bugs.python.org/issue19643
    # https://bugs.python.org/msg218021
    if issubclass(exc_info[0], WindowsError) and exc_info[1].winerror == 5:
        os.chmod(path, stat.S_IWRITE)
        return remove(path)
    raise exc_info[1]


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
            shutil.rmtree(target, onerror=_rmtree_readonly)
        shutil.copytree(url, target)
        app_log.info('Copied %s into %s', url, target)
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
    if os.path.exists(target):
        shutil.rmtree(target, onerror=_rmtree_readonly)
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
    if os.path.exists(config.target):
        shutil.rmtree(config.target, onerror=_rmtree_readonly)
    proc = Popen(appcmd, bufsize=-1, stdout=sys.stdout, stderr=sys.stderr)
    proc.communicate()


setup_paths = AttrDict()
setup_paths['make'] = {
    'file': 'Makefile',
    'cmd': '"$EXE"'
}
setup_paths['powershell'] = {
    'file': 'setup.ps1',
    'cmd': '"$EXE" -File "$FILE"'
}
setup_paths['bash'] = {
    'file': 'setup.sh',
    'cmd': '"$EXE" "$FILE"'
}
setup_paths['python'] = {
    'file': 'setup.py',
    'cmd': '"$EXE" "$FILE"'
}
setup_paths['npm'] = {
    'file': 'package.json',
    'cmd': '"$EXE" install'
}
setup_paths['bower'] = {
    'file': 'bower.json',
    'cmd': '"$EXE" install'
}


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
    apps_config['cmd'] = {appname: args}
    app_config = (+apps_config).get(appname, {})
    app_config.target = str(app_dir / app_config.get('target', appname))
    return app_config


def install(cmd, args):
    if len(cmd) < 1:
        apps = (+apps_config).keys()
        app_log.error('gramex install [%s]', '|'.join(apps))
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


def uninstall(cmd, args):
    if len(cmd) < 1:
        apps = (+apps_config['user']).keys()
        app_log.error('gramex uninstall [%s]', '|'.join(apps))
        return
    if len(cmd) > 1 and args:
        app_log.error('Arguments allowed only with single app. Ignoring %s', ', '.join(cmd[1:]))
        cmd = cmd[:1]

    for appname in cmd:
        app_log.info('Uninstalling: %s', appname)

        # Delete the target directory if it exists
        app_config = get_app_config(appname, args)
        if os.path.exists(app_config.target):
            if app_config.target.startswith(variables['GRAMEXDATA']):
                shutil.rmtree(app_config.target, onerror=_rmtree_readonly)
            else:
                app_log.warn('Not removing directory %s (outside $GRAMEXDATA)', app_config.target)
        else:
            app_log.error('No directory %s to remove', app_config.target)
        save_user_config(appname, None)


def run(cmd, args):
    if len(cmd) < 1:
        apps = (+apps_config['user']).keys()
        app_log.error('gramex run [%s]', '|'.join(apps))
        return
    if len(cmd) > 1:
        app_log.error('Can only run one app. Ignoring %s', ', '.join(cmd[1:]))

    appname = cmd.pop(0)
    app_log.info('Initializing %s on Gramex %s', appname, gramex.__version__)

    app_config = get_app_config(appname, args)
    target = app_config.target
    if 'dir' in app_config:
        target = os.path.join(target, app_config.dir)
    if os.path.isdir(target):
        os.chdir(target)
        gramex.paths['base'] = Path('.')
        # If we run with updated parameters, save them for the next run
        app_config.update({key: val for key, val in args.items() if key in app_keys})
        app_config.setdefault('run', {}).update(
            {key: val for key, val in args.items() if key not in app_keys})
        save_user_config(appname, app_config)
        gramex.init(cmd=AttrDict(app=app_config['run']))
    else:
        app_log.error('No directory %s to run for %s', app_config.target, appname)
