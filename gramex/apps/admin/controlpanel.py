"""Auth module role settings."""
import os
import json
import datetime
import gramex
from gramex import variables
from gramex.handlers.basehandler import SQLiteStore

path = os.path.join(variables.GRAMEXDATA, 'auth.user.db')
user_info = SQLiteStore(path, table='user')


def get_config_id(handler):
    if handler.kwargs.get('admin_kwargs', '') == '':
        handler.kwargs.admin_kwargs = {'hide': []}

    return json.dumps({
        'id': handler.kwargs.variables.get('id', None),
        'hide': handler.kwargs.admin_kwargs.get('hide', []),
        'forgot_key': handler.kwargs.admin_kwargs.get('forgot_key', 'forgot'),
        'login_url': handler.kwargs.auth.get('login_url')
    })


def active_users():
    all_users = {}
    for key in user_info.keys():
        all_users[key] = user_info.load(key)
    return json.dumps({
        user: 1 for user, info in all_users.items()
        if info.get('active') == 'y'
    })


def is_admin(handler, admin_user=None, admin_role=None):
    user = handler.current_user
    admin_identifiers = {
        'id': admin_user,
        'role': admin_role
    }
    for key, value in admin_identifiers.items():
        if value is not None:
            if isinstance(value, str) and user.get(key, None) == value:
                return True
            if isinstance(value, (list,)) and user.get(key, None) in value:
                return True
    # TODO: REVIEW: make this choice based on YAML Variable $DEBUG(=True) instead
    if handler.request.remote_ip in ('127.0.0.1', '::1'):
        return True
    return False


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
            if(other_user is not None and other_user.get('id') and
               arg_user == other_user.get('id')):
                session.pop('user')
                user_dets = user_info.load(arg_user)
                user_dets.update({'active': ''})
                user_info.dump(arg_user, user_dets)
    return {'status': 'ok'}


def last_login():
    """Get last login details."""
    user_logs_path = os.path.join(
        variables.GRAMEXDATA, 'authmodule', 'user.csv')
    names = ['time', 'event', 'sid', 'user', 'ip', 'user-agent']
    if os.path.exists(user_logs_path):
        data = gramex.cache.open(
            user_logs_path, 'csv', header=None, names=names)
        dt = datetime.datetime.strptime(
            data.tail(1)['time'].values[0], "%Y-%m-%d %H:%M:%SZ")
        return dt
    return ''
