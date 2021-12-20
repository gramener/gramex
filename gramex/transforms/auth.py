'''
Authentication transforms
'''
from gramex.config import app_log


def ensure_single_session(handler):
    '''
    Ensure that user in this session is logged out of all other sessions.
    '''
    user_id = handler.session.get(handler.session_user_key, {}).get('id')
    if user_id is None:
        return
    # Go through every session and drop user from every other session
    for key in handler._session_store.keys():
        # Ignore current session or OTP sessions
        if key == handler.session.get('id'):
            continue
        if isinstance(key, str) and key.startswith('otp:'):
            continue
        if isinstance(key, bytes) and key.startswith(b'otp:'):
            continue
        # Remove user from all other sessions
        other_session = handler._session_store.load(key)
        if not isinstance(other_session, dict):
            continue
        other_user = other_session.get(handler.session_user_key)
        if isinstance(other_user, dict) and other_user.get('id') == user_id:
            other_session = dict(other_session)
            other_session.pop(handler.session_user_key)
            handler._session_store.dump(key, other_session)
            app_log.debug('ensure_single_session: dropped user %s from session %s',
                          user_id, other_session['id'])
