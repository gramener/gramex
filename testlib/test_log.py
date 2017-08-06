import os
import json
import time
import inspect
import unittest
from tornado.log import access_log
from gramex.handlers.basehandler import log_method
from test_transforms import eqfn


class TestLogMethod(unittest.TestCase):
    @classmethod
    def setupClass(cls):
        cls.folder = os.path.dirname(os.path.abspath(__file__))
        cls.methods = []

    def test_csv(self):
        writer, handle = None, None

        def log_request(handler, writer=writer, handle=handle):
            writer.writerow([
                round(time.time() * 1000, 0),
                handler.request.method,
                handler.request.uri,
                handler.request.remote_ip,
                handler.get_status(),
                round(handler.request.request_time() * 1000, 0),
                json.dumps(handler.current_user),
                getattr(handler, "_exception", ""),
                handler.get_argument("x", ""),
                getattr(handler.request, "scheme", ""),
                handler.request.headers.get("X-Gramex-Key", ""),
                handler.request.cookies["sid"].value if "sid" in handler.request.cookies else "",
                (handler.current_user or {}).get("email", ""),
                os.environ.get("HOME", ""),
            ])
            handle.flush()
        result = log_method(dict(
            format='csv',
            path=os.path.join(self.folder, 'handler.csv'),
            keys=['time', 'method', 'uri', 'ip', 'status', 'duration', 'user', 'error',
                  'args.x', 'request.scheme', 'headers.X-Gramex-Key', 'cookies.sid',
                  'user.email', 'env.HOME']
        ))
        self.methods.append(result)
        eqfn(result, log_request)

    def test_format(self):
        log_format = None

        def log_request(handler, logger=access_log):
            obj = {}
            status = obj['status'] = handler.get_status()
            obj["time"] = round(time.time() * 1000, 0)
            obj["method"] = handler.request.method
            obj["uri"] = handler.request.uri
            obj["ip"] = handler.request.remote_ip
            obj["status"] = handler.get_status()
            obj["duration"] = round(handler.request.request_time() * 1000, 0)
            obj["user"] = json.dumps(handler.current_user)
            obj["error"] = getattr(handler, "_exception", "")
            obj["args.x"] = handler.get_argument("x", "")
            obj["request.scheme"] = getattr(handler.request, "scheme", "")
            obj["headers.X-Gramex-Key"] = handler.request.headers.get("X-Gramex-Key", "")
            obj["cookies.sid"] = handler.request.cookies["sid"].value if "sid" in handler.request.cookies else ""       # noqa
            obj["user.email"] = (handler.current_user or {}).get("email", "")
            obj["env.HOME"] = os.environ.get("HOME", "")
            if status < 400:        # noqa
                logger.info(log_format % obj)
            elif status < 500:      # noqa
                logger.warning(log_format % obj)
            else:
                logger.error(log_format % obj)
        result = log_method(dict(
            format='%(time)f%(method)s%(uri)s%(ip)s%(status)s%(duration)s%(user)s%(error)s'
                   '%(args.x)s%(request.scheme)s%(headers.X-Gramex-Key)s%(cookies.sid)s'
                   '%(user.email)s%(env.HOME)s'
        ))
        self.methods.append(result)
        eqfn(result, log_request)

    @classmethod
    def teardownClass(cls):
        for method in cls.methods:
            handle = dict(inspect.getmembers(method))['func_globals'].get('handle')
            if handle:
                if not handle.closed:
                    handle.close()
                if os.path.exists(handle.name):
                    os.unlink(handle.name)
