"""Auth module role settings."""
import sys
from tornado.web import HTTPError
from cachetools import TTLCache
from six.moves import StringIO
import gramex
from gramex.config import app_log
from gramex.http import INTERNAL_SERVER_ERROR
from gramex.handlers import FormHandler, DBAuth

contexts = TTLCache(maxsize=100, ttl=1800)


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
    if authhandler not in gramex.conf.get('url', {}):
        raise ValueError('Missing url.%s (cannot find authhandler)' % authhandler)
    auth_conf = gramex.conf.url[authhandler]
    auth_kwargs = auth_conf.get('kwargs', {})
    if 'lookup' in auth_kwargs:
        data_conf = auth_kwargs['lookup'].copy()
        return authhandler, auth_conf, data_conf
    elif auth_conf.get('handler', None) == 'DBAuth':
        # For DBAuth, hoist the user.column into as the id: for the URL
        user_column = auth_kwargs.get('user', {}).get('column', 'user')
        data_conf = DBAuth.clear_special_keys(auth_kwargs.copy(), 'user',
                                              'password', 'forgot', 'signup')
        data_conf['id'] = user_column
        return authhandler, auth_conf, data_conf
    else:
        raise ValueError('Missing lookup: in url.%s (authhandler)' % authhandler)


class AdminFormHandler(FormHandler):
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
            super(FormHandler, cls).setup(**kwargs)
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
