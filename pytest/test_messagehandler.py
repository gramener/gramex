import gramex.data
import json
import os
import pytest
import time
from websocket import create_connection
from utils import is_gramex_running

GRAMEX_PORT = os.environ.get('GRAMEX_PORT', '9999')
DELAY = 0.01
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'messages.db')

if not is_gramex_running(GRAMEX_PORT):
    pytest.skip(f'gramex is not running on port {GRAMEX_PORT}', allow_module_level=True)


def test_configuration():
    url = f'ws://localhost:{GRAMEX_PORT}/messagehandler/simple'
    ws = create_connection(url)
    body = f'Hello {time.time()}'
    ws.send(json.dumps({'_method': 'POST', 'body': body}))
    ws.close()
    time.sleep(DELAY)
    # Test that table has a new array
    result = gramex.data.filter(f'sqlite:///{DB_PATH}', table='simple', args={'body': [body]})
    assert len(result) == 1
    for column in ('id', 'user', 'timestamp', 'body'):
        assert column in result.columns
