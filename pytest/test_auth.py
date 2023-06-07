import json
import os
import requests
from tornado.web import create_signed_value

GRAMEX_PORT = os.environ.get('GRAMEX_PORT', '9999')
COOKIE_SECRET = 'secret-key'


def test_user_permissions():
    # Test all combinations
    #   app=None | value
    #   namespace=None | value
    #   project=None | value
    #   user=None | with only user_permissions | with only roles | with both
    assert requests.get(
        f'http://localhost:{GRAMEX_PORT}/auth/user', headers=user_header(id='alpha')
    ).json() == {'id': 'alpha', 'permissions': [], 'roles': []}


def user_header(**user):
    return {'X-Gramex-User': create_signed_value(COOKIE_SECRET, 'user', json.dumps(user))}
