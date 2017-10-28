import os
import time
import datetime
import unittest
from gramex import conf
from gramex.handlers.basehandler import build_log_info
from .test_transforms import eqfn


class TestLog(unittest.TestCase):
    def test_log_info(self):
        def log_info(handler, event):
            return {
                'name': handler.name,
                'class': handler.__class__.__name__,
                'time': round(time.time() * 1000, 0),
                'datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ'),
                'method': handler.request.method,
                'uri': handler.request.uri,
                'ip': handler.request.remote_ip,
                'status': handler.get_status(),
                'duration': round(handler.request.request_time() * 1000, 0),
                'port': conf.app.listen.port,
                'user': (handler.current_user or {}).get("id", ""),
                'error': getattr(handler, "_exception", ""),
                'args.x': handler.get_argument("x", ""),
                'request.scheme': getattr(handler.request, "scheme", ""),
                'headers.X-Gramex-Key': handler.request.headers.get("X-Gramex-Key", ""),
                'cookies.sid': (handler.request.cookies["sid"].value
                                if "sid" in handler.request.cookies else ""),
                'user.email': (handler.current_user or {}).get("email", ""),
                'env.HOME': os.environ.get("HOME", ""),
                'event': event,
            }
        result = build_log_info([
            'name', 'class', 'time', 'datetime', 'method', 'uri', 'ip', 'status', 'duration',
            'port', 'user', 'error', 'args.x', 'request.scheme',
            'headers.X-Gramex-Key', 'cookies.sid', 'user.email', 'env.HOME', 'event'
        ], 'event')
        eqfn(actual=result, expected=log_info)
