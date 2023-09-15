import requests
import pytest
from utils import gramex_port

GRAMEX_PORT = gramex_port()
if not gramex_port():
    pytest.skip(f'gramex is not running on port {GRAMEX_PORT}', allow_module_level=True)

DELAY = 0.01
MSG = 'OK?'


class TestValidate(object):
    def test_arg_key(self):
        base = f'http://localhost:{GRAMEX_PORT}/validate'
        assert requests.get(f'{base}/false').status_code == 400
        assert requests.get(f'{base}/true').status_code == 200
        assert requests.get(f'{base}/zero').status_code == 400
        assert requests.get(f'{base}/one').status_code == 200
        assert requests.get(f'{base}/string').status_code == 400
        assert requests.get(f'{base}/string?x=1').status_code == 200
        assert requests.get(f'{base}/string?x=2').status_code == 400
        assert requests.get(f'{base}/list').status_code == 400
        assert requests.get(f'{base}/list?x=1').status_code == 400
        assert requests.get(f'{base}/list?x=1&y=2').status_code == 200
        assert requests.get(f'{base}/dict').status_code == 400
        assert requests.get(f'{base}/dict?x=1').status_code == 200
        assert requests.get(f'{base}/list-dict').status_code == 400
        assert requests.get(f'{base}/list-dict?x=1').status_code == 400
        assert requests.get(f'{base}/list-dict?x=1&y=2').status_code == 200
        r = requests.get(f'{base}/params')
        assert r.status_code == 451
        assert r.reason == 'x is not 1'
        r = requests.get(f'{base}/params?x=1')
        assert r.status_code == 452
        assert r.reason == 'y missing'
