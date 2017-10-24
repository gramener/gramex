import os
import time
import unittest
from gramex.handlers.basehandler import build_log_info
from .test_transforms import eqfn


class TestLog(unittest.TestCase):
    def test_log_info(self):
        def log_info(handler):
            return {
                'time': round(time.time() * 1000, 0),
                'method': handler.request.method,
                'uri': handler.request.uri,
                'ip': handler.request.remote_ip,
                'status': handler.get_status(),
                'duration': round(handler.request.request_time() * 1000, 0),
                'user': handler.current_user.get("id", ""),
                'error': getattr(handler, "_exception", ""),
                'args.x': handler.get_argument("x", ""),
                'request.scheme': getattr(handler.request, "scheme", ""),
                'headers.X-Gramex-Key': handler.request.headers.get("X-Gramex-Key", ""),
                'cookies.sid': (handler.request.cookies["sid"].value
                                if "sid" in handler.request.cookies else ""),
                'user.email': (handler.current_user or {}).get("email", ""),
                'env.HOME': os.environ.get("HOME", ""),
            }
        result = build_log_info(keys=[
            'time', 'method', 'uri', 'ip', 'status', 'duration', 'user', 'error', 'args.x',
            'request.scheme', 'headers.X-Gramex-Key', 'cookies.sid', 'user.email', 'env.HOME'])
        eqfn(actual=result, expected=log_info)
