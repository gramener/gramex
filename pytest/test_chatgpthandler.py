import os
import pytest
from websocket import create_connection, WebSocket
from utils import gramex_port

GRAMEX_PORT = gramex_port()
if not gramex_port():
    pytest.skip(f'gramex is not running on port {GRAMEX_PORT}', allow_module_level=True)

DELAY = 0.01
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'messages.db')
MSG = 'OK?'


def send(url: str, msg: str):
    ws = create_connection(url, timeout=3)
    ws.send(msg)
    return ws


def recv(ws: WebSocket):
    response = None
    while not response:
        response = ws.recv()
    return response


class TestKey(object):
    def test_no_key(self):
        ws = send(f'ws://localhost:{GRAMEX_PORT}/chatgpthandler/no-key', MSG)
        assert recv(ws) == '[ERROR]\nmessage: No API key\ntype: invalid_request_error'

    def test_wrong_key(self):
        ws = send(f'ws://localhost:{GRAMEX_PORT}/chatgpthandler/wrong-key', MSG)
        assert recv(ws) == '[ERROR]\nmessage: Wrong API key\ntype: invalid_request_error'

    def test_string_key(self):
        ws = send(f'ws://localhost:{GRAMEX_PORT}/chatgpthandler/string-key', MSG)
        assert recv(ws) == MSG

    def test_arg_key(self):
        ws = send(f'ws://localhost:{GRAMEX_PORT}/chatgpthandler/arg-key?key=TEST-KEY', MSG)
        assert recv(ws) == MSG
        ws = send(f'ws://localhost:{GRAMEX_PORT}/chatgpthandler/arg-key', MSG)
        assert recv(ws) == '[ERROR]\nmessage: Wrong API key\ntype: invalid_request_error'


class TestAPI(object):
    def test_http_error(self):
        ws = send(f'ws://localhost:{GRAMEX_PORT}/chatgpthandler/http-error', MSG)
        assert recv(ws) == '[ERROR] [Errno 10061] Unknown error'

    def test_transforms(self):
        ws = send(f'ws://localhost:{GRAMEX_PORT}/chatgpthandler/transforms', MSG)
        assert recv(ws) == f'INIT\npre:{MSG}:post'


class TestHistory(object):
    def test_default_history(self):
        ws = create_connection(f'ws://localhost:{GRAMEX_PORT}/chatgpthandler/string-key')
        for x in range(10):
            ws.send(str(x))
            assert recv(ws) == '\n'.join(str(v) for v in range(x + 1))

    def test_max_history(self):
        ws = create_connection(f'ws://localhost:{GRAMEX_PORT}/chatgpthandler/history?max=3')
        for x in range(10):
            ws.send(str(x))
            assert recv(ws) == '\n'.join(str(v) for v in list(range(x + 1))[-4:])


class TestStream(object):
    def test_stream(self):
        ws = send(f'ws://localhost:{GRAMEX_PORT}/chatgpthandler/stream', MSG)
        # Collect all responses streamed in, but don't wait for more than len(MSG) attemps
        result = ''
        for _attempt in range(len(MSG)):
            result += recv(ws)
            if len(result) >= len(MSG):
                break
        assert result == MSG
