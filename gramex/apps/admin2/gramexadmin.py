"""Auth module role settings."""
import gramex
import gramex.handlers
import json
import os
import re
import sys
from binascii import b2a_base64
from cachetools import TTLCache
from gramex.config import app_log
from gramex.http import INTERNAL_SERVER_ERROR
from six.moves import StringIO
from tornado.gen import coroutine, Return
from tornado.web import HTTPError


contexts = TTLCache(maxsize=100, ttl=1800)
# A global mapping of cid: to filenames
cidmap = TTLCache(maxsize=100, ttl=1800)


def get_auth_conf(kwargs):
    '''
    Expects kwargs.authhandler to point to an AuthHandler key in gramex config.
    The AuthHandler must have a lookup.
    Returns the authhandler, its configuration, and the FormHandler data configuration.
    Used in AdminFormHandler *and* in index.html. So keep it as a separate function.
    '''
    if 'authhandler' not in kwargs:
        raise ValueError('Missing authhandler')
    authhandler = kwargs['authhandler']
    # The authhandler key may be prefixed with a namespace. Find the *first* matching key
    for key, auth_conf in gramex.conf.get('url', {}).items():
        if key == authhandler or key.endswith(':' + authhandler):
            break
    else:
        raise ValueError('Missing url.%s (cannot find authhandler)' % authhandler)
    auth_kwargs = auth_conf.get('kwargs', {})
    if 'lookup' in auth_kwargs:
        data_conf = auth_kwargs['lookup'].copy()
        return authhandler, auth_conf, data_conf
    elif auth_conf.get('handler', None) == 'DBAuth':
        # For DBAuth, hoist the user.column into as the id: for the URL
        user_column = auth_kwargs.get('user', {}).get('column', 'user')
        data_conf = gramex.handlers.DBAuth.clear_special_keys(
            auth_kwargs.copy(), 'user', 'password', 'forgot', 'signup', 'template', 'delay')
        data_conf['id'] = user_column
        return authhandler, auth_conf, data_conf
    else:
        raise ValueError('Missing lookup: in url.%s (authhandler)' % authhandler)


class AdminFormHandler(gramex.handlers.FormHandler):
    '''
    A customized FormHandler. Specify a "kwargs.admin_kwargs.authhandler: auth-handler".
    It lookup up "auth-handler" in the gramex config. If it has a "lookup:" or is a "DBAuth",
    creates a FormHandler using that url: and other parameters.
    '''
    @classmethod
    def setup(cls, **kwargs):
        # admin_kwargs.authhandler is a url: key that holds an AuthHandler. Get its kwargs
        try:
            authhandler, auth_conf, data_conf = get_auth_conf(kwargs.get('admin_kwargs', {}))
        except ValueError as e:
            super(gramex.handlers.FormHandler, cls).setup(**kwargs)
            app_log.warning('%s: %s', cls.name, e.args[0])
            cls.reason = e.args[0]
            cls.get = cls.post = cls.put = cls.delete = cls.send_response
            return
        # Get the FormHandler configuration from lookup:
        cls.conf.kwargs = data_conf
        super(AdminFormHandler, cls).setup(**cls.conf.kwargs)

    def send_response(self, *args, **kwargs):
        raise HTTPError(INTERNAL_SERVER_ERROR, reason=self.reason)


def evaluate(handler, code):
    """Evaluates Python code in a WebSocketHandler, like a REPL"""
    retval = None
    # Check if code is an expression (eval) or statement (exec)
    try:
        co, mode = compile(code, '<input>', 'eval'), 'eval'
    except SyntaxError:
        try:
            co, mode = compile(code, '<input>', 'exec'), 'exec'
        except Exception as e:
            retval = e
    except Exception as e:
        retval = e
    if retval is not None:
        handler.write_message(repr(retval))
        return

    # Capture stdout
    old_stdout, out = sys.stdout, StringIO()
    sys.stdout = out
    # Run code and get the result. (Result is None for exec)
    try:
        context = contexts.setdefault(handler.session['id'], {})
        context['handler'] = handler
        if mode == 'eval':
            result = eval(co, context)
        else:
            exec(co, context)
            result = None
    except Exception as e:
        result = e
    finally:
        sys.stdout = old_stdout

    # Write the stdout (if any), then the returned value (if any)
    retval = out.getvalue()
    if result is not None:
        retval += repr(result)
    handler.write_message(retval)


@coroutine
def system_information(handler):
    '''Handler for system info'''
    value, error = {}, {}
    try:
        import psutil
        process = psutil.Process(os.getpid())
        value['system', 'cpu-count'] = psutil.cpu_count()
        value['system', 'cpu-usage'] = psutil.cpu_percent()
        value['system', 'memory-usage'] = psutil.virtual_memory().percent
        value['system', 'disk-usage'] = psutil.disk_usage('/').percent
        value['gramex', 'memory-usage'] = process.memory_info()[0]
        value['gramex', 'open-files'] = len(process.open_files())
    except ImportError:
        app_log.warning('psutil required for system stats')
        error['system', 'cpu-count'] = 'psutil not installed'
        error['system', 'cpu-usage'] = 'psutil not installed'
        error['system', 'memory-usage'] = 'psutil not installed'
        error['system', 'disk-usage'] = 'psutil not installed'
        error['gramex', 'memory-usage'] = 'psutil not installed'
        error['gramex', 'open-files'] = 'psutil not installed'
    try:
        import conda
        value['conda', 'version'] = conda.__version__,
    except ImportError:
        app_log.warning('conda required for conda stats')
        error['conda', 'version'] = 'conda not installed'

    from shutilwhich import which
    value['node', 'path'] = which('node')
    value['git', 'path'] = which('git')

    from gramex.cache import Subprocess
    apps = {
        ('node', 'version'): Subprocess('node --version', shell=True),
        ('npm', 'version'): Subprocess('npm --version', shell=True),
        ('yarn', 'version'): Subprocess('yarn --version', shell=True),
        ('git', 'version'): Subprocess('git --version', shell=True),
    }
    for key, proc in apps.items():
        stdout, stderr = yield proc.wait_for_exit()
        value[key] = stdout.strip()
        if not value[key]:
            error[key] = stderr.strip()

    value['python', 'version'] = '{0}.{1}.{2}'.format(*sys.version_info[:3])
    value['python', 'path'] = sys.executable
    value['gramex', 'version'] = gramex.__version__
    value['gramex', 'path'] = os.path.dirname(gramex.__file__)

    import pandas as pd
    df = pd.DataFrame({'value': value, 'error': error}).reset_index()
    df.columns = ['section', 'key'] + df.columns[2:].tolist()
    df = df[['section', 'key', 'value', 'error']].sort_values(['section', 'key'])
    df['error'] = df['error'].fillna('')
    data = gramex.data.filter(df, handler.args)
    # TODO: handle _format, _meta, _download, etc just like FormHandler
    raise Return(gramex.data.download(data))


def get_schedule(service_type):
    import json
    import pandas as pd
    from cron_descriptor import get_description

    data = []
    for key, info in gramex.conf.get(service_type, {}).items():
        entry = dict(info)
        entry['name'] = key
        entry['args'] = json.dumps(entry.get('args', []))
        entry['kwargs'] = json.dumps(entry.get('kwargs', {}))
        entry['schedule'] = ''
        if key not in gramex.service[service_type]:
            entry['schedule'] = 'NA'
            data.append(entry)
            continue
        schedule = gramex.service[service_type][key]
        entry['next'] = schedule.next * 1000 if schedule.next else None
        if hasattr(schedule, 'cron_str'):
            cron = schedule.cron_str
            # cron_descriptor requires year to start with a number
            if cron.endswith(' *'):
                cron = cron[:-2]
            entry['schedule'] = get_description(cron)
            entry['schedule'] += ' UTC' if schedule.utc else ''
        entry['startup'] = 'Y' if entry.get('startup', False) else ''
        entry['thread'] = 'Y' if entry.get('thread', False) else ''
        data.append(entry)
    return pd.DataFrame(data)


@coroutine
def schedule(handler, service):
    if handler.request.method == 'GET':
        data = get_schedule(service)
        data = gramex.data.filter(data, handler.args)
        # TODO: handle _format, _meta, _download, etc just like FormHandler
        raise Return(gramex.data.download(data))
    elif handler.request.method == 'POST':
        key = handler.get_argument('name')
        schedule = gramex.service[service][key]
        results, kwargs = [], {}
        # If ?mock is set, and it's an alert, capture the alert mails in result
        if handler.get_argument('mock', False) and service == 'alert':
            kwargs = {'callback': lambda **kwargs: results.append(kwargs)}
        if schedule.thread:
            args = yield schedule.function(**kwargs)
        else:
            args = yield gramex.service.threadpool.submit(schedule.function, **kwargs)
        if service == 'alert' and isinstance(args, dict):
            for arg in args.get('fail', []):
                raise arg['error']
        for result in results:
            if 'html' in result:
                def _img(match):
                    path = result['images'][match.group(1)]
                    img = gramex.cache.open(path, 'bin', transform=b2a_base64)
                    url = b'data:image/png;base64,' + img.replace(b'\n', b'')
                    return url.decode('utf-8')
                result['html'] = re.sub(r'cid:([^\'"\s]+)', _img, result['html'])
        raise Return(json.dumps(results))
