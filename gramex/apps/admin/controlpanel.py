"""Auth module role settings."""
import os
import sys
import json
import datetime
from cachetools import TTLCache
from io import StringIO
import gramex
from gramex import variables
from gramex.cache import SQLiteStore

path = os.path.join(variables.GRAMEXDATA, 'auth.user.db')
user_info = SQLiteStore(path, table='user')
contexts = TTLCache(maxsize=100, ttl=1800)


def get_config_id(handler):
    if handler.kwargs.get('admin_kwargs', '') == '':
        handler.kwargs.admin_kwargs = {'hide': []}

    return json.dumps(
        {
            'id': handler.kwargs.variables.get('id', None),
            'hide': handler.kwargs.admin_kwargs.get('hide', []),
            'forgot_key': handler.kwargs.admin_kwargs.get('forgot_key', 'forgot'),
            'login_url': handler.kwargs.auth.get('login_url'),
        }
    )


def active_users():
    all_users = {}
    for key in user_info.keys():
        all_users[key] = user_info.load(key)
    return json.dumps({user: 1 for user, info in all_users.items() if info.get('active') == 'y'})


def is_admin(handler, admin_user=None, admin_role=None):
    user = handler.current_user
    admin_identifiers = {'id': admin_user, 'role': admin_role}
    for key, value in admin_identifiers.items():
        if value is not None:
            if isinstance(value, str) and user.get(key, None) == value:
                return True
            if isinstance(value, (list,)) and user.get(key, None) in value:
                return True
    # TODO: REVIEW: make this choice based on YAML Variable $DEBUG(=True) instead
    return handler.request.remote_ip in ('127.0.0.1', '::1')


def user_sessions(handler):
    """Determine user sessions then determine active sessions."""
    sessions = {}
    for key in handler._session_store.keys():
        user = handler.session.get('user', {})
        sessions[key] = user
    return sessions


def pop_user(handler):
    """Pop user from session."""
    arg_user = handler.get_argument('user', {})
    sessions = user_sessions(handler)
    for key in sessions:
        session = handler._session_store.load(key)
        if session is not None:
            other_user = session.get('user')
            if (
                other_user is not None
                and other_user.get('id')
                and arg_user == other_user.get('id')
            ):
                session.pop('user')
                user_dets = user_info.load(arg_user)
                user_dets.update({'active': ''})
                user_info.dump(arg_user, user_dets)
    return {'status': 'ok'}


def last_login():
    """Get last login details."""
    user_logs_path = os.path.join(variables.GRAMEXDATA, 'authmodule', 'user.csv')
    names = ['time', 'event', 'sid', 'user', 'ip', 'user-agent']
    if os.path.exists(user_logs_path):
        data = gramex.cache.open(user_logs_path, 'csv', header=None, names=names)
        dt = datetime.datetime.strptime(data.tail(1)['time'].values[0], "%Y-%m-%d %H:%M:%SZ")
        return dt
    return ''


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
        # B307:eval B102:exec_used is safe since only admin can run this
        if mode == 'eval':
            result = eval(co, context)  # nosec B307
        else:
            exec(co, context)  # nosec B102
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
