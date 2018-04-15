"""Auth module role settings."""
import os
import json
import gramex
import datetime
from gramex import variables
from gramex.handlers.basehandler import SQLiteStore

path = os.path.join(variables.GRAMEXDATA, 'auth.user.db')
user_info = SQLiteStore(path, table='user')


def get_config_id(handler):
    return json.dumps(handler.kwargs.variables.get('id', None))


def active_users():
    all_users = {}
    for key in user_info.keys():
        all_users[key] = user_info.load(key)
    return json.dumps({
        user: 1 for user, info in all_users.items()
        if info.get('active')
    })


def is_admin(handler, admin_user=None, admin_role=None):
    user = handler.current_user
    # Check if admin_user is None, str, list, ...
    # TODO: IMP: `role` is not yet done`
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


def last_login():
    """Get last login details."""
    user_logs_path = os.path.join(
        variables.GRAMEXDATA, 'authmodule', 'user.csv')
    names = ['time', 'event', 'sid', 'user', 'ip', 'user-agent']
    if os.path.exists(user_logs_path):
        data = gramex.cache.open(user_logs_path, 'csv', header=None, names=names)
        dt = datetime.datetime.strptime(
            data.tail(1)['time'].values[0], "%Y-%m-%d %H:%M:%SZ")
        return dt
    return ''
