'''
Defines command line services to install, setup and run apps.
'''
from __future__ import unicode_literals

import io
import os
import six
import sys
import yaml
import stat
import shlex
import shutil
import datetime
import requests
from shutilwhich import which
from pathlib import Path
from subprocess import Popen, check_output, CalledProcessError      # nosec
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from zipfile import ZipFile
from tornado.template import Template
from orderedattrdict.yamlutils import from_yaml         # noqa
import gramex
from gramex.config import ChainConfig, PathConfig, variables, app_log

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
    setup.sh, requirements.txt, setup.py, yarn/npm install and bower install.

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
        - yarn/npm install
        - bower install

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
    usage: gramex init [--target=DIR]

    Initializes a Gramex project at the current or target dir. Specifically, it:
    - Sets up a git repo
    - Install supporting files for a gramex project
    - Runs gramex setup (which runs yarn/npm install and other dependencies)

mail: |
    gramex mail <key>               # Send mail named <key>
    gramex mail --list              # Lists all keys in config file
    gramex mail --init              # Initializes config file

    The config is a gramex.yaml file. It must have email: and alert: sections.
    $GRAMEXDATA/mail/gramexmail.yaml is the default config file.

    Options:
      --conf <path>                 # Specify a different conf file location
'''
usage = yaml.load(usage, Loader=AttrDictYAMLLoader)     # nosec


class TryAgainError(Exception):
    '''If shutil.rmtree fails, and we've fixed the problem, raise this to try again'''
    pass


try:
    WindowsError
except NameError:
    # On non-Windows systems, _ensure_remove just raises the exception
    def _ensure_remove(remove, path, exc_info):     # noqa -- redefine function
        raise exc_info[1]
else:
    # On Windows systems, try harder
    def _ensure_remove(function, path, exc_info):
        '''onerror callback for rmtree that tries hard to delete files'''
        if issubclass(exc_info[0], WindowsError):
            import winerror
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
                import time
                delays = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
                for delay in delays:
                    time.sleep(delay)
                    try:
                        return os.remove(path)
                    except WindowsError:
                        pass
            # npm creates windows shortcuts that shutil.rmtree cannot delete.
            # os.listdir failes with a PATH_NOT_FOUND. Delete these and try again
            elif function == os.listdir and exc_info[1].winerror == winerror.ERROR_PATH_NOT_FOUND:
                app_log.error('Cannot delete %s', path)
                from win32com.shell import shell, shellcon
                options = shellcon.FOF_NOCONFIRMATION | shellcon.FOF_NOERRORUI
                code, err = shell.SHFileOperation((0, shellcon.FO_DELETE, path, None, options))
                if code == 0:
                    raise TryAgainError()
        raise exc_info[1]


def safe_rmtree(target):
    '''
    A replacement for shutil.rmtree that removes directories within $GRAMEXDATA.
    It tries to remove the target multiple times, recovering from errors.
    '''
    if not os.path.exists(target):
        return True
    # TODO: check case insensitive in Windows, but case sensitive on other OS
    elif target.lower().startswith(variables['GRAMEXDATA'].lower()):
        # Try multiple times to recover from errors, since we have no way of
        # auto-resuming rmtree: https://bugs.python.org/issue8523
        for count in range(100):
            try:
                shutil.rmtree(target, onerror=_ensure_remove)
            except TryAgainError:
                pass
            else:
                break
        return True
    else:
        app_log.warning('Not removing directory %s (outside $GRAMEXDATA)', target)
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
    # If the app is a Cygwin app, TARGET should be a Cygwin path too.
    target = config.target
    cygcheck, cygpath, kwargs = which('cygcheck'), which('cygpath'), {'universal_newlines': True}
    if cygcheck is not None and cygpath is not None:
        app_path = check_output([cygpath, '-au', which(appcmd[0])], **kwargs).strip()   # nosec
        is_cygwin_app = check_output([cygcheck, '-f', app_path], **kwargs).strip()      # nosec
        if is_cygwin_app:
            target = check_output([cygpath, '-au', target], **kwargs).strip()           # n osec
    # Replace TARGET with the actual target
    if 'TARGET' in appcmd:
        appcmd = [target if arg == 'TARGET' else arg for arg in appcmd]
    else:
        appcmd.append(target)
    app_log.info('Running %s', ' '.join(appcmd))
    if not safe_rmtree(config.target):
        app_log.error('Cannot delete target %s. Aborting installation', config.target)
        return
    proc = Popen(appcmd, bufsize=-1, stdout=sys.stdout, stderr=sys.stderr, **kwargs)    # nosec
    proc.communicate()
    return proc.returncode


# Setup file configurations.
# Structure: {File: {exe: cmd}}
# If File exists, then if exe exists, run cmd.
# For example, if package.json exists:
#   then if yarn exists, run yarn install
#   else if npm exists, run npm install
setup_paths = '''
Makefile:
    make: '"{EXE}"'
setup.ps1:
    powershell: '"{EXE}" -File "{FILE}"'
setup.sh:
    bash: '"{EXE}" "{FILE}"'
requirements.txt:
    pip: '"{EXE}" install -r "{FILE}"'
setup.py:
    python: '"{EXE}" "{FILE}"'
package.json:
    yarn: '"{EXE}" install --prefer-offline'
    npm: '"{EXE}" install'
bower.json:
    bower: '"{EXE}" --allow-root install'
'''
setup_paths = yaml.load(setup_paths, Loader=AttrDictYAMLLoader)     # nosec


def run_setup(target):
    '''
    Install any setup file in target directory. Target directory can be:

    - An absolute path
    - A relative path to current directory
    - A relative path to the Gramex apps/ folder

    Returns the absolute path of the final target path.

    This supports:

    - ``make`` (if Makefile exists)
    - ``powershell -File setup.ps1``
    - ``bash setup.sh``
    - ``pip install -r requirements.txt``
    - ``python setup.py``
    - ``yarn install`` else ``npm install``
    - ``bower --allow-root install``
    '''
    if not os.path.exists(target):
        app_target = os.path.join(variables['GRAMEXPATH'], 'apps', target)
        if not os.path.exists(app_target):
            raise OSError('No directory %s' % target)
        target = app_target
    target = os.path.abspath(target)
    app_log.info('Setting up %s', target)
    for file, runners in setup_paths.items():
        setup_file = os.path.join(target, file)
        if not os.path.exists(setup_file):
            continue
        for exe, cmd in runners.items():
            exe_path = which(exe)
            if exe_path is not None:
                cmd = cmd.format(FILE=setup_file, EXE=exe_path)
                app_log.info('Running %s', cmd)
                _run_console(cmd, cwd=target)
                break
        else:
            app_log.warning('Skipping %s. No %s found', setup_file, exe)


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


def get_app_config(appname, args):
    '''
    Get the stored configuration for appname, and override it with args.
    ``.target`` defaults to $GRAMEXDATA/apps/<appname>.
    '''
    apps_config['cmd'] = {appname: args}
    app_config = AttrDict((+apps_config).get(appname, {}))
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
        run_install(app_config)
    elif 'url' in app_config:
        run_install(app_config)
    elif 'cmd' in app_config:
        returncode = run_command(app_config)
        if returncode != 0:
            app_log.error('Command failed with return code %d. Aborting installation', returncode)
            return
    else:
        app_log.error('Use --url=... or --cmd=... to specific source of %s', appname)
        return

    # Post-installation
    app_config.target = run_setup(app_config.target)
    app_config['installed'] = {'time': datetime.datetime.utcnow()}
    save_user_config(appname, app_config)
    app_log.info('Installed. Run `gramex run %s`', appname)


def setup(cmd, args):
    for target in cmd:
        run_setup(target)
        return
    if 'all' in args:
        root = os.path.join(variables['GRAMEXPATH'], 'apps')
        for filename in os.listdir(root):
            target = os.path.join(root, filename)
            # Only run setup on directories. Ignore __pycache__, etc
            if os.path.isdir(target) and not filename.startswith('_'):
                run_setup(target)
        return
    app_log.error(show_usage('setup'))


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
        cline = ' '.join('--%s=%s' % arg for arg in flatten_config(app_config.get('run', {})))
        app_log.info('Gramex %s | %s %s | %s | Python %s', gramex.__version__, appname, cline,
                     os.getcwd(), sys.version.replace('\n', ' '))
        gramex.init(cmd=AttrDict(app=app_config['run']))
    elif appname in apps_config['user']:
        # The user configuration has a wrong path. Inform user
        app_log.error('%s: no directory %s', appname, app_config.target)
        app_log.error('Run "gramex uninstall %s" and try again.', appname)
    else:
        app_log.error('%s: no directory %s', appname, app_config.target)


def service(cmd, args):
    try:
        import gramex.winservice
    except ImportError:
        app_log.error('Unable to load winservice. Is this Windows?')
        raise
    if len(cmd) < 1:
        app_log.error(show_usage('service'))
        return
    gramex.winservice.GramexService.setup(cmd, **args)


def _check_output(cmd, default=b'', **kwargs):
    '''Run cmd and return output. Return default in case the command fails'''
    try:
        return check_output(shlex.split(cmd), **kwargs).strip()     # nosec
    except CalledProcessError:
        return default


def _run_console(cmd, **kwargs):
    '''Run cmd and  pipe output to console (sys.stdout / sys.stderr)'''
    proc = Popen(shlex.split(cmd), bufsize=-1, stdout=sys.stdout, stderr=sys.stderr,
                 universal_newlines=True, **kwargs)
    proc.communicate()


def init(cmd, args):
    '''Create Gramex scaffolding files.'''
    if len(cmd) > 1:
        app_log.error(show_usage('init'))
        return
    args.setdefault('target', os.getcwd())
    app_log.info('Initializing Gramex project at %s', args.target)
    data = {
        'appname': os.path.basename(args.target),
        'author': _check_output('git config user.name', default='Author'),
        'email': _check_output('git config user.email', default='user@example.org'),
        'date': datetime.datetime.today().strftime('%Y-%m-%d')
    }
    # Create a git repo if required
    if not os.path.exists(os.path.join(args.target, '.git')):
        _run_console('git init')
    # Copy all files as templates
    source_dir = os.path.join(variables['GRAMEXPATH'], 'apps', 'init')
    for path in os.listdir(source_dir):
        target = os.path.join(args.target, path)
        if os.path.exists(target):
            app_log.warning('Skipping existing %s', path)
            continue
        with io.open(os.path.join(source_dir, path), 'rb') as handle:
            result = Template(handle.read()).generate(**data)
        with io.open(target, 'wb') as handle:
            handle.write(result)
    run_setup(args.target)


default_mail_config = r'''# Gramex mail configuration at
# List keys with "gramex mail --list --conf={confpath}"

# See https://learn.gramener.com/guide/email/ for help
email:
  default-email:
    type: gmail
    email: $GRAMEXMAILUSER
    password: $GRAMEXMAILPASSWORD
    # Uncomment the next line to test the application without sending mails
    # stub: log

# See https://learn.gramener.com/guide/alert/
alert:
  hello-world:
    to: admin@example.org
    subject: Alert from Gramex
    body: |
      This is a test email
'''


def mail(cmd, args):
    # Get config file location
    default_dir = os.path.join(variables['GRAMEXDATA'], 'mail')
    if not os.path.exists(default_dir):
        os.makedirs(default_dir)
    confpath = args.get('conf', os.path.join(default_dir, 'gramexmail.yaml'))

    if not os.path.exists(confpath):
        if 'init' in args:
            with io.open(confpath, 'w', encoding='utf-8') as handle:
                handle.write(default_mail_config.format(confpath=confpath))
            app_log.info('Initialized %s', confpath)
        elif not cmd and not args:
            app_log.error(show_usage('mail'))
        else:
            app_log.error('Missing config %s. Use --init to generate skeleton', confpath)
        return

    conf = PathConfig(confpath)
    if 'list' in args:
        for key, alert in conf.get('alert', {}).items():
            to = alert.get('to', '')
            if isinstance(to, list):
                to = ', '.join(to)
            gramex.console('{:15}\t"{}" to {}'.format(key, alert.get('subject'), to))
        return

    if 'init' in args:
        app_log.error('Config already exists at %s', confpath)
        return

    if len(cmd) < 1:
        app_log.error(show_usage('mail'))
        return

    from gramex.services import email as setup_email, create_alert
    alert_conf = conf.get('alert', {})
    email_conf = conf.get('email', {})
    setup_email(email_conf)
    for key in cmd:
        if key not in alert_conf:
            app_log.error('Missing key %s', key)
            continue
        alert = create_alert(key, alert_conf[key])
        alert()
