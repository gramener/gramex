'''
Defines command line services to install, setup and run apps.
'''
import contextlib
import io
import os
import sys
import time
import yaml
import stat
import shlex
import string
import shutil
import datetime
import requests
from shutil import which
from pathlib import Path

# B404:import_subprocess only developers can access this, not users
from subprocess import Popen, check_output, CalledProcessError  # nosec B404
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from zipfile import ZipFile
from tornado.template import Template
import gramex
import gramex.license
from gramex.config import ChainConfig, PathConfig, variables, app_log, slug

usage = '''
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

    After installation, runs "gramex setup" which runs the Makefile, setup.ps1,
    setup.sh, requirements.txt, setup.py, bower install, npm install, yarn install.

    Installed apps:
    {apps}

setup: |
    usage: gramex setup <target> [<target> ...] [--all]

    target is the directory to set up (required). This can be an absolute path,
    relative path, or a directory name under $GRAMEXPATH/apps/.

    gramex setup --all sets up all apps under $GRAMEXPATH/apps/

    Run the following commands at that directory in sequence, if possible:
        - make
        - powershell -File setup.ps1
        - bash setup.sh
        - pip install --upgrade -r requirements.txt
        - python setup.py
        - bower --allow-root install
        - npm install
        - yarn install --prefer-offline

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

service: |
    usage: gramex service <cmd> [--options]

    Install a Gramex application as a Windows service:

        gramex service install
            --cwd  "C:/path/to/application/"
            --user "DOMAIN\\USER"                # Optional user to run as
            --password "user-password"          # Required if user is specified
            --startup manual|auto|disabled

    Update:

        gramex service update <same parameters as install>

    Remove:

        gramex service remove       # or gramex service uninstall

    Start / stop commands

        gramex service start
        gramex service stop

init: |
    gramex init [--target=DIR]
    gramex init minimal [--target=DIR]

    Initializes a Gramex project at the current or target dir. Specifically, it:
    - Sets up a git repo
    - Install supporting files for a Gramex project from a template
      - "gramex init" sets up dependencies for a local system
      - "gramex init minimal" sets up minimal dependencies
    - Runs gramex setup (which runs npm install and other dependencies)

    Options:
      --target <path>               # Location to install at. Defaults to

mail: |
    gramex mail <key>               # Send mail named <key>
    gramex mail --list              # Lists all keys in config file
    gramex mail --init              # Initializes config file

    The config is a gramex.yaml file. It must have email: and alert: sections.
    If the current folder has a gramex.yaml, that's used. Else the default is
    $GRAMEXDATA/mail/gramexmail.yaml.

    Options:
      --conf <path>                 # Specify a different conf file location

license: |
    gramex license                  # Show Gramex license
    gramex license accept           # Accept Gramex license
    gramex license reject           # Reject Gramex license
'''
# B506:yaml_load yaml.load is safe since it only reads the string above, not user-created content
usage = yaml.load(usage, Loader=AttrDictYAMLLoader)  # nosec B506


class TryAgainError(Exception):
    '''If shutil.rmtree fails, and we've fixed the problem, raise this to try again'''

    pass


try:
    WindowsError
except NameError:
    # On non-Windows systems, _ensure_remove just raises the exception
    def _ensure_remove(remove, path, exc_info):
        raise exc_info[1]

else:
    # On Windows systems, try harder
    def _ensure_remove(func, path, exc_info):
        '''onerror callback for rmtree that tries hard to delete files'''
        if issubclass(exc_info[0], WindowsError):
            winerror = AttrDict(
                ERROR_PATH_NOT_FOUND=3,
                ERROR_ACCESS_DENIED=5,
                ERROR_SHARING_VIOLATION=32,
            )
            # Delete read-only files
            # https://bugs.python.org/issue19643
            # https://bugs.python.org/msg218021
            if exc_info[1].winerror == winerror.ERROR_ACCESS_DENIED:
                os.chmod(path, stat.S_IWRITE)
                return os.remove(path)
            # Delay delete a bit if directory is used by another process.
            # Typically happens on uninstall immediately after bower / npm / git
            # (e.g. during testing.)
            elif exc_info[1].winerror == winerror.ERROR_SHARING_VIOLATION:
                delays = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
                for delay in delays:
                    time.sleep(delay)
                    with contextlib.suppress(WindowsError):
                        return os.remove(path)
            # npm creates windows shortcuts that shutil.rmtree cannot delete.
            # os.listdir/scandir fails with a PATH_NOT_FOUND.
            # Delete these using win32com and try again.
            elif exc_info[1].winerror == winerror.ERROR_PATH_NOT_FOUND and func in {
                os.listdir,
                os.scandir,
            }:
                app_log.error(f'Cannot delete {path}')
                from win32com.shell import shell, shellcon  # type:ignore

                options = shellcon.FOF_NOCONFIRMATION | shellcon.FOF_NOERRORUI
                code, err = shell.SHFileOperation((0, shellcon.FO_DELETE, path, None, options))
                if code == 0:
                    raise TryAgainError()
        raise exc_info[1]


def _try_remove(target, retries=100, delay=0.05, func=shutil.rmtree, **kwargs):
    for _index in range(retries):
        try:
            func(target, **kwargs)
        except TryAgainError:
            pass
        # If permission is denied, e.g. antivirus, file is open, etc, keep trying with delay
        except OSError:
            app_log.warning('    Trying again to delete', target)
            time.sleep(delay)
        else:
            break


def safe_rmtree(target, retries=100, delay=0.05, gramexdata=True):
    '''
    A replacement for shutil.rmtree and os.remove that removes directories,
    optionally within $GRAMEXDATA.
    It tries to remove the target multiple times, recovering from errors.
    '''
    if not os.path.exists(target):
        return True
    # TODO: check case insensitive in Windows, but case sensitive on other OS
    func, kwargs = (
        (shutil.rmtree, {'onerror': _ensure_remove}) if os.path.isdir(target) else (os.remove, {})
    )
    if gramexdata:
        if target.lower().startswith(variables['GRAMEXDATA'].lower()):
            # Try multiple times to recover from errors, since we have no way of
            # auto-resuming rmtree: https://bugs.python.org/issue8523
            _try_remove(target, retries, delay, func, **kwargs)
            return True
        else:
            app_log.warning(f'Not removing directory {target} (outside $GRAMEXDATA)')
            return False
    else:
        _try_remove(target, retries, delay, func, **kwargs)


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


def run_install(config):
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
            url = os.path.abspath(url).lower().rstrip(os.sep)
            target = os.path.abspath(target).lower().rstrip(os.sep)
            if url != target and not safe_rmtree(target):
                return
        if url != target:
            shutil.copytree(url, target)
            app_log.info(f'Copied {url} into {target}')
        config.url = url
        return

    # If it's a file, unzip it
    if os.path.exists(url):
        handle = url
    else:
        # Otherwise, assume that it's a URL containing a ZIP file
        app_log.info(f'Downloading: {url}')
        response = requests.get(url)
        response.raise_for_status()
        handle = io.BytesIO(response.content)

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
        app_log.info(f'Extracted {len(files)} files into {target}')


def run_command(config):
    '''
    Run config.cmd. If the command has a TARGET, replace it with config.target.
    Else append config.target as an argument.
    '''
    appcmd = config.cmd
    # Split the command into an array of words
    if isinstance(appcmd, str):
        appcmd = shlex.split(appcmd)
    # If the app is a Cygwin app, TARGET should be a Cygwin path too.
    target = config.target
    cygwin, cygpath, kwargs = which('cygcheck'), which('cygpath'), {'universal_newlines': True}
    if cygwin is not None and cygpath is not None:
        # subprocess.check_output is safe here since these are developer-initiated
        # B404:import_subprocess check_output is safe here since these are developer-initiated
        path = check_output([cygpath, '-au', which(appcmd[0])], **kwargs).strip()  # nosec 404
        is_cygwin_app = check_output([cygwin, '-f', path], **kwargs).strip()  # nosec 404
        if is_cygwin_app:
            target = check_output([cygpath, '-au', target], **kwargs).strip()  # nosec 404
    # Replace TARGET with the actual target
    if 'TARGET' in appcmd:
        appcmd = [target if arg == 'TARGET' else arg for arg in appcmd]
    else:
        appcmd.append(target)
    app_log.info(f'Running {" ".join(appcmd)}')
    if not safe_rmtree(config.target):
        app_log.error(f'Cannot delete target {config.target}. Aborting installation')
        return
    # B603:subprocess_without_shell_equals_true is safe since this is developer-initiated
    proc = Popen(appcmd, bufsize=-1, **kwargs)  # nosec 603
    proc.communicate()
    return proc.returncode


# Setup file configurations. If {file} exists, then if {exe} exists, run {cmd}.
setup_paths = [
    [{'file': 'Makefile', 'exe': 'make', 'cmd': '"{exe}"'}],
    [{'file': 'setup.ps1', 'exe': 'powershell', 'cmd': '"{exe}" -File "{file}"'}],
    [{'file': 'setup.sh', 'exe': 'bash', 'cmd': '"{exe}" "{file}"'}],
    [{'file': 'requirements.txt', 'exe': 'pip', 'cmd': '"{exe}" install -r "{file}"'}],
    [{'file': 'setup.py', 'exe': 'python', 'cmd': '"{exe}" "{file}"'}],
    [{'file': 'bower.json', 'exe': 'bower', 'cmd': '"{exe}" --allow-root install'}],
    [
        {'file': 'package-lock.json', 'exe': 'npm', 'cmd': '"{exe}" ci'},
        {'file': 'yarn.lock', 'exe': 'yarn', 'cmd': '"{exe}" install --prefer-offline'},
        {'file': 'package.json', 'exe': 'npm', 'cmd': '"{exe}" install'},
        {'file': 'package.json', 'exe': 'yarn', 'cmd': '"{exe}" install --prefer-offline'},
    ],
]


def run_setup(target):
    '''
    Install any setup file in target directory. Target directory can be:

    - An absolute path
    - A relative path to current directory
    - A relative path to the Gramex apps/ folder

    Returns the absolute path of the final target path.
    '''
    if not os.path.exists(target):
        app_target = os.path.join(variables['GRAMEXPATH'], 'apps', target)
        if not os.path.exists(app_target):
            raise OSError(f'No directory {target}')
        target = app_target
    target = os.path.abspath(target)
    app_log.info(f'Setting up {target}')
    for configs in setup_paths:
        config_match, ran_cmd = None, False
        for config in configs:
            setup_file = os.path.join(target, config['file'])
            exe_path = which(config['exe'])
            if os.path.exists(setup_file):
                config_match = config
            if config_match and exe_path is not None:
                cmd = config['cmd'].format(file=setup_file, exe=exe_path)
                app_log.info(f'Running {cmd}')
                _run_console(cmd, cwd=target)
                ran_cmd = True
                break
        if config_match and not ran_cmd:
            app_log.warning(f'Skipping {config_match["file"]}. No {config_match["exe"]} found')


app_dir = Path(variables.get('GRAMEXDATA')) / 'apps'
if not app_dir.exists():
    app_dir.mkdir(parents=True)

# Get app configuration by chaining apps.yaml in gramex + app_dir + command line
apps_config = ChainConfig()
apps_config['base'] = PathConfig(gramex.paths['source'] / 'apps.yaml')
user_conf_file = app_dir / 'apps.yaml'
apps_config['user'] = PathConfig(user_conf_file) if user_conf_file.exists() else AttrDict()

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
    if user_conf_file.exists():
        with user_conf_file.open(encoding='utf-8') as handle:
            user_config = yaml.safe_load(handle)
    if value is None:
        if appname in user_config:
            del user_config[appname]
    else:
        app_config = user_config.setdefault(appname, AttrDict())
        app_config.update({key: value[key] for key in app_keys if key in value})

    with user_conf_file.open(mode='w', encoding='utf-8') as handle:
        yaml.safe_dump(user_config, handle, indent=4, default_flow_style=False)


def get_app_config(appname, kwargs):
    '''
    Get the stored configuration for appname, and override it with kwargs.
    ``.target`` defaults to $GRAMEXDATA/apps/<appname>.
    '''
    apps_config['cmd'] = {appname: kwargs}
    app_config = AttrDict((+apps_config).get(appname, {}))
    app_config.setdefault('target', str(app_dir / app_config.get('target', appname)))
    app_config.target = os.path.abspath(app_config.target)
    return app_config


def flatten_config(config, base=None):
    'Get flattened configurations'
    for key, value in config.items():
        keystr = key if base is None else base + '.' + key
        if hasattr(value, 'items'):
            yield from flatten_config(value, keystr)
        else:
            yield keystr, value


def show_usage(command):
    apps = (+apps_config).keys()
    return 'gramex {command}\n\n{desc}'.format(
        command=command,
        desc=usage[command].strip().format(apps='\n'.join('- ' + app for app in sorted(apps))),
    )


def install(args, kwargs):
    if len(args) < 1:
        app_log.error(show_usage('install'))
        return

    appname = args[0]
    app_log.info(f'Installing: {appname}')
    app_config = get_app_config(appname, kwargs)
    if len(args) == 2:
        app_config.url = args[1]
        run_install(app_config)
    elif 'url' in app_config:
        run_install(app_config)
    elif 'cmd' in app_config:
        returncode = run_command(app_config)
        if returncode != 0:
            app_log.error(f'Command failed with return code {returncode}. Aborting installation')
            return
    else:
        app_log.error(f'Use --url=... or --cmd=... to specific source of {appname}')
        return

    # Post-installation
    app_config.target = run_setup(app_config.target)
    app_config['installed'] = {'time': datetime.datetime.utcnow()}
    save_user_config(appname, app_config)
    app_log.info(f'Installed. Run `gramex run {appname}`')


def setup(args, kwargs):
    for target in args:
        run_setup(target)
        return
    if 'all' in kwargs:
        root = os.path.join(variables['GRAMEXPATH'], 'apps')
        for filename in os.listdir(root):
            target = os.path.join(root, filename)
            # Only run setup on directories. Ignore __pycache__, etc
            if os.path.isdir(target) and not filename.startswith('_'):
                run_setup(target)
        return
    app_log.error(show_usage('setup'))


def uninstall(args, kwargs):
    if len(args) < 1:
        app_log.error(show_usage('uninstall'))
        return
    if len(args) > 1 and kwargs:
        app_log.errorf(f'Arguments allowed only with single app. Ignoring {", ".join(args[1:])}')
        args = args[:1]

    for appname in args:
        app_log.info(f'Uninstalling: {appname}')

        # Delete the target directory if it exists
        app_config = get_app_config(appname, kwargs)
        if os.path.exists(app_config.target):
            safe_rmtree(app_config.target)
        else:
            app_log.error(f'No directory {app_config.target} to remove')
        save_user_config(appname, None)


def run(args, kwargs):
    if len(args) < 1:
        app_log.error(show_usage('run'))
        return
    if len(args) > 1:
        app_log.error(f'Can only run one app. Ignoring {", ".join(args[1:])}')

    appname = args.pop(0)
    app_config = get_app_config(appname, kwargs)

    target = app_config.target
    if 'dir' in app_config:
        target = os.path.join(target, app_config.dir)
    if os.path.isdir(target):
        os.chdir(target)
        gramex.paths['base'] = Path('.')
        # If we run with updated parameters, save for next run under the .run config
        run_config = app_config.setdefault('run', {})
        for key in kwargs:
            if key not in app_keys:
                run_config[key] = app_config.pop(key)
        save_user_config(appname, app_config)
        # Tell the user what configs are used
        cline = ' '.join('--%s=%s' % arg for arg in flatten_config(app_config.get('run', {})))
        app_log.info(
            'Gramex %s | %s %s | %s | Python %s',
            gramex.__version__,
            appname,
            cline,
            os.getcwd(),
            sys.version.replace('\n', ' '),
        )
        gramex.init(args=AttrDict(app=app_config['run']))
    elif appname in apps_config['user']:
        # The user configuration has a wrong path. Inform user
        app_log.error(
            f'{appname}: no target path {app_config.target}. '
            f'Run "gramex uninstall {appname}" and try again.',
        )
    else:
        app_log.error(f'{appname}: no target path {app_config.target}')


def service(args, kwargs):
    '''Install, remove, start or stop Gramex as a Windows service.'''
    try:
        import gramex.winservice
    except ImportError:
        app_log.error('Unable to load winservice. Is this Windows?')
        raise
    if len(args) < 1:
        app_log.error(show_usage('service'))
        return
    gramex.winservice.GramexService.setup(args, **kwargs)


def _check_output(cmd, default=b'', **kwargs):
    '''Run cmd and return output. Return default in case the command fails'''
    try:
        # B603:subprocess_without_shell_equals_true is safe since this is developer-initiated
        return check_output(shlex.split(cmd), **kwargs).strip()  # nosec B603
    # OSError is raised if the cmd is not found.
    # CalledProcessError is raised if the cmd returns an error.
    except (OSError, CalledProcessError):
        return default


def _run_console(cmd, **kwargs):
    '''Run cmd and pipe output to console. Log and raise error if cmd is not found'''
    cmd = shlex.split(cmd)
    try:
        # B603:subprocess_without_shell_equals_true is safe since this is developer-initiated
        proc = Popen(cmd, bufsize=-1, universal_newlines=True, **kwargs)  # nosec B603
    except OSError:
        app_log.error(f'Cannot find command: {cmd[0]}')
        raise
    proc.communicate()


def _mkdir(path):
    '''Create directory tree up to path if path does not exist'''
    if not os.path.exists(path):
        os.makedirs(path)


def init(args, kwargs):
    '''Create Gramex scaffolding files.'''
    if len(args) > 2:
        app_log.error(show_usage('init'))
        return
    if len(args) == 0:
        args.append('default')
    source_dir = os.path.join(variables['GRAMEXPATH'], 'apps', 'init', args[0])
    if not os.path.exists(source_dir):
        app_log.error(f'Unknown init template {args[0]}')

    kwargs.setdefault('target', os.getcwd())
    app_log.info(f'Initializing Gramex project at {kwargs.target}')
    data = {
        'appname': os.path.basename(kwargs.target),
        'author': _check_output('git config user.name', default='Author'),
        'email': _check_output('git config user.email', default='user@example.org'),
        'date': datetime.datetime.today().strftime('%Y-%m-%d'),
        'version': gramex.__version__,
    }
    # Ensure that appname is a valid Python module name
    appname = slug.module(data['appname'])
    if appname[0] not in string.ascii_lowercase:
        appname = 'app' + appname
    data['appname'] = appname

    # Create a git repo. But if git fails, do not stop. Continue with the rest.
    with contextlib.suppress(OSError):
        _run_console('git init')
    # Install Git LFS if available. Set git_lfs=None if it fails, so .gitignore ignores assets/**
    data['git_lfs'] = which('git-lfs')
    if data['git_lfs']:
        try:
            _run_console('git lfs install')
            _run_console('git lfs track "assets/**"')
        except OSError:
            data['git_lfs'] = None

    # Copy all directories & files. Files with '.template.' are treated as templates.
    for root, dirs, files in os.walk(source_dir):
        relpath = os.path.relpath(root, start=source_dir)
        for name in dirs + files:
            source = os.path.join(root, name)
            targetname = name.replace('$appname', appname)
            template_data = None
            if '.template.' in name:
                targetname, template_data = name.replace('.template.', '.'), data
            target = os.path.join(kwargs.target, relpath, targetname)
            if os.path.exists(target):
                app_log.warning(f'Skip existing {target}')
            elif os.path.isdir(source):
                _mkdir(target)
            elif os.path.isfile(source):
                app_log.info(f'Copy file {source}')
                with io.open(source, 'rb') as handle:
                    result = handle.read()
                    if template_data is not None:
                        result = Template(result).generate(**template_data)
                with io.open(target, 'wb') as handle:
                    handle.write(result)
            else:
                app_log.warning(f'Skip unknown file {source}')

    run_setup(kwargs.target)


default_mail_config = r'''# Gramex mail configuration at
# List keys with "gramex mail --list --conf={confpath}"

# See https://gramener.com/gramex/guide/email/ for help
email:
  default-email:
    type: gmail
    email: $GRAMEXMAILUSER
    password: $GRAMEXMAILPASSWORD
    # Add stub: log to test the application without sending mails

# See https://gramener.com/gramex/guide/alert/
alert:
  hello-world:
    to: admin@example.org
    subject: Alert from Gramex
    body: |
      This is a test email
'''


def mail(args, kwargs):
    # Get config file location
    default_dir = os.path.join(variables['GRAMEXDATA'], 'mail')
    _mkdir(default_dir)
    if 'conf' in kwargs:
        confpath = kwargs.conf
    elif os.path.exists('gramex.yaml'):
        confpath = os.path.abspath('gramex.yaml')
    else:
        confpath = os.path.join(default_dir, 'gramexmail.yaml')

    if not os.path.exists(confpath):
        if 'init' in kwargs:
            with io.open(confpath, 'w', encoding='utf-8') as handle:
                handle.write(default_mail_config.format(confpath=confpath))
            app_log.info(f'Initialized {confpath}')
        elif not args and not kwargs:
            app_log.error(show_usage('mail'))
        else:
            app_log.error(f'Missing config {confpath}. Use --init to generate skeleton')
        return

    conf = PathConfig(confpath)
    if 'list' in kwargs:
        for key, alert in conf.get('alert', {}).items():
            to = alert.get('to', '')
            if isinstance(to, list):
                to = ', '.join(to)
            gramex.console('{:15}\t"{}" to {}'.format(key, alert.get('subject'), to))
        return

    if 'init' in kwargs:
        app_log.error(f'Config already exists at {confpath}')
        return

    if len(args) < 1:
        app_log.error(show_usage('mail'))
        return

    from gramex.services import email as setup_email, create_alert

    alert_conf = conf.get('alert', {})
    email_conf = conf.get('email', {})
    setup_email(email_conf)
    sys.path += os.path.dirname(confpath)
    for key in args:
        if key not in alert_conf:
            app_log.error(f'Missing key {key} in {confpath}')
            continue
        alert = create_alert(key, alert_conf[key])
        alert()


def license(args, kwargs):
    if len(args) == 0:
        gramex.console(gramex.license.EULA)
        if gramex.license.is_accepted():
            gramex.console('License already ACCEPTED. Run "gramex license reject" to reject')
        else:
            gramex.console('License NOT YET accepted. Run "gramex license accept" to accept')
    elif args[0] == 'accept':
        gramex.license.accept(force=True)
    elif args[0] == 'reject':
        gramex.license.reject()
    else:
        app_log.error(f'Invalid command license {args[0]}')
