'''
Authentication transforms
'''
from __future__ import unicode_literals
import six
from gramex.config import app_log


def ensure_single_session(handler):
    '''
    Ensure that user in this session is logged out of all other sessions.
    '''
    user_id = handler.session.get('user', {}).get('id')
    if user_id is not None:
        for key in handler._session_store.keys():
            # Ignore current session or OTP sessions
            if key == handler.session.get('id'):
                continue
            if isinstance(key, six.text_type) and key.startswith('otp:'):
                continue
            if isinstance(key, six.binary_type) and key.startswith(b'otp:'):
                continue
            # Remove user from all other sessions
            other_session = handler._session_store.load(key)
            if other_session is not None:
                other_user = other_session.get('user')
                if other_user is not None and other_user.get('id'):
                    other_session.pop('user')
                    handler._session_store.dump(key, other_session)
                    app_log.debug('dropped user %s from session %s', user_id, other_session['id'])
