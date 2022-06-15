'''Authentication transforms'''
from gramex.config import app_log


def ensure_single_session(handler):
    '''Log user out of all sessions except this handler's.

    This is used in any auth handler, e.g. [SimpleAuth][gramex.handlers.SimpleAuth]
    or [GoogleAuth][gramex.handlers.GoogleAuth], as a login action:

    ```yaml
    pattern: /login/
    handler: GoogleAuth     # or any auth
    kwargs:
        action:
            - function: ensure_single_session
    ```

    It removes the user object from all sessions except the session of this handler.
    '''
    user_id = handler.session.get(handler.session_user_key, {}).get('id')
    if user_id is None:
        return
    # Go through every session and drop user from every other session
    for key in handler._session_store.keys():
        # Ignore current session or OTP / API key sessions
        if key == handler.session.get('id'):
            continue
        bytekey = key.encode('utf-8') if isinstance(key, str) else key
        if bytekey.startswith(b'otp:') or bytekey.startswith(b'key:'):
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
            app_log.debug(f'ensure_single_session: dropped user {user_id} from session {key}')
