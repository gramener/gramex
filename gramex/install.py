import os
import six
import sys
import yaml
import shlex
import shutil
import logging
import datetime
import requests
from pathlib import Path
from subprocess import Popen
from orderedattrdict import AttrDict
from zipfile import ZipFile
import gramex
from gramex.config import ChainConfig, PathConfig, variables


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


def download_zip(url, target, contentdir=True, rootdir=None):
    '''
    Download url into path. url can be http, https, ftp. It will be unzipped
    based on its type.
    '''
    # If the URL is a directory, copy it
    if os.path.isdir(url):
        if os.path.exists(target):
            shutil.rmtree(target)
        shutil.copytree(url, target)
        return

    # If it's a file, unzip it
    if os.path.exists(url):
        handle = url
    else:
        # Otherwise, assume that it's a URL containing a ZIP file
        logging.info('Downloading: %s', url)
        response = requests.get(url)
        response.raise_for_status()
        handle = six.BytesIO(response.content)

    zipfile = ZipFile(handle)
    members = zipfile.infolist()
    if contentdir:
        prefix = os.path.commonprefix(zipfile.namelist())
        if prefix.endswith('/'):
            members = zip_prefix_filter(members, prefix)
    if rootdir is not None:
        rootdir = rootdir.replace('\\', '/')
        if not rootdir.endswith('/'):
            rootdir += '/'
        members = zip_prefix_filter(members, rootdir)

    if len(members):
        if os.path.exists(target):
            shutil.rmtree(target)
        zipfile.extractall(target, members)
        logging.info('Extracted %d files into %s', len(members), target)
    else:
        logging.warn('No files after filtering %s with root dir %s', url, rootdir)


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
    'rootdir': 'Sub-directory under "url" to install (optional)',
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
        logging.error('gramex install [%s]', '|'.join(apps))
        return
    if len(cmd) > 1 and args:
        logging.error('Arguments allowed only with single app. Ignoring %s', ', '.join(cmd[1:]))
        cmd = cmd[:1]

    for appname in cmd:
        logging.info('Installing: %s', appname)
        app_config = get_app_config(appname, args)
        if 'url' in app_config:
            # Download the app URL into target directory
            download_zip(
                url=app_config.url,
                target=app_config.target,
                contentdir=app_config.get('contentdir', True),
                rootdir=app_config.get('rootdir', None),
            )
            app_config['installed'] = {'time': datetime.datetime.utcnow()}
            save_user_config(appname, app_config)
        elif 'cmd' in app_config:
            appcmd = app_config.cmd
            if isinstance(appcmd, six.string_types):
                appcmd = shlex.split(appcmd)
            if '$TARGET' in appcmd:
                appcmd = [app_config.target if arg == '$TARGET' else arg for arg in appcmd]
            else:
                appcmd.append(app_config.target)
            proc = Popen(appcmd, bufsize=-1, stdout=sys.stdout, stderr=sys.stderr)
            proc.communicate()
            save_user_config(appname, app_config)
        else:
            logging.error('Use --url=... or --cmd=... to specific source of %s', appname)


def uninstall(cmd, args):
    if len(cmd) < 1:
        apps = (+apps_config['user']).keys()
        logging.error('gramex uninstall [%s]', '|'.join(apps))
        return
    if len(cmd) > 1 and args:
        logging.error('Arguments allowed only with single app. Ignoring %s', ', '.join(cmd[1:]))
        cmd = cmd[:1]

    for appname in cmd:
        logging.info('Uninstalling: %s', appname)

        # Delete the target directory if it exists
        app_config = get_app_config(appname, args)
        if os.path.exists(app_config.target):
            if app_config.target.startswith(variables['GRAMEXDATA']):
                shutil.rmtree(app_config.target)
            else:
                logging.warn('Not removing directory %s (outside $GRAMEXDATA)', app_config.target)
        else:
            logging.error('No directory %s to remove', app_config.target)
        save_user_config(appname, None)


def run(cmd, args):
    if len(cmd) < 1:
        apps = (+apps_config['user']).keys()
        logging.error('gramex run [%s]', '|'.join(apps))
        return
    if len(cmd) > 1:
        logging.error('Can only run one app. Ignoring %s', ', '.join(cmd[1:]))

    appname = cmd.pop(0)
    logging.info('Initializing %s on Gramex %s', appname, gramex.__version__)

    app_config = get_app_config(appname, args)
    if os.path.exists(app_config.target):
        os.chdir(app_config.target)
        gramex.paths['base'] = Path('.')
        # If we run with updated parameters, save them for the next run
        app_config.update({key: val for key, val in args.items() if key in app_keys})
        app_config.setdefault('run', {}).update(
            {key: val for key, val in args.items() if key not in app_keys})
        save_user_config(appname, app_config)
        gramex.init(cmd=AttrDict(app=app_config['run']))
    else:
        logging.error('No directory %s to run', app_config.target)
