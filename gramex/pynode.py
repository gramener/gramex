'''
Python Node.js bridge
'''
import os
import re
import json
from shutil import which
from tornado.gen import coroutine, sleep
from tornado.websocket import websocket_connect, WebSocketClosedError
from gramex.config import variables
from gramex.cache import daemon
from gramex.config import app_log

_info = {}


class Node:
    '''
    Usage::

        node = Node(port=9966, node_path='/tmp/')
        total = await node.js('return {"total": x + y}', x='a', y=10)['total']
    '''

    _source = os.path.join(variables['GRAMEXAPPS'], 'pynode')
    _delay = 0.01

    def __init__(self, port=9966, cwd=None, node_path=None, timeout=10):
        self.port = port
        # cwd is the directory where node runs. Defaults to $GRAMEXDATA/pynode/
        # node_modules is updated under this.
        self.cwd = os.path.join(variables['GRAMEXDATA'], 'pynode') if cwd is None else cwd
        if not os.path.exists(self.cwd):
            os.makedirs(self.cwd)
        # node_path is where the node executable is. Autodetect from PATH by default
        self.node_path = node_path or which('node')
        self.url = f'ws://127.0.0.1:{port}'
        self.timeout = timeout
        self.proc, self.conn = None, None
        self.count = 0

    @coroutine
    def js(self, code=None, path=None, **kwargs):
        if self.conn is None:
            try:
                self.conn = yield websocket_connect(self.url, connect_timeout=self.timeout)
            except OSError as exc:
                import errno

                if exc.errno != errno.ECONNREFUSED:
                    raise
                self.proc = yield daemon(
                    [
                        self.node_path,
                        os.path.join(self._source, 'index.js'),
                        f'--port={self.port}',
                    ],
                    first_line=re.compile(r'pynode: 1.\d+.\d+ port: %s' % self.port),
                    cwd=self.cwd,
                    # New node modules will be installed in self.cwd.
                    # But pynode/index.js also uses its own packages.
                    # So set NODE_PATH to both node_modules. Node will require() from both.
                    env=dict(
                        os.environ,
                        NODE_PATH=os.pathsep.join(
                            [
                                os.path.join(self._source, 'node_modules'),
                                os.path.join(self.cwd, 'node_modules'),
                            ]
                        ),
                    ),
                )
                self.conn = yield websocket_connect(self.url, connect_timeout=self.timeout)

        # code= takes preference over path=
        if code is not None:
            kwargs['code'] = code
        elif path is not None:
            kwargs['path'] = path

        # Send the commands. If node has died, clear the connection.
        try:
            yield self.conn.write_message(json.dumps(kwargs))
        except WebSocketClosedError:
            r, self.conn = {'error': 'Cannot write to Node.js', 'result': None}, None
            app_log.error(r['error'])
            return r

        # Receive the response.
        # Note: read_message() cannot be called again while a request is running.
        # (Yes, that's odd. Maybe Anand is missing something.)
        # So wait until the read_future is cleared.
        while getattr(self.conn, 'read_future', None) is not None:
            yield sleep(self._delay)
        msg = yield self.conn.read_message()
        # If node has died, clear the connection and retry.
        if msg is None:
            r, self.conn = {'error': 'Cannot read from Node.js', 'result': None}, None
            app_log.error(r['error'])
            return r

        # Parse the result as JSON. Log errors if any
        r = json.loads(msg)
        if r.get('error', None):
            app_log.error(r['error'])
        return r


# Create pynode.node lazily -- only on first request
def __getattr__(name):
    if name == 'node':
        if 'node' not in _info:
            _info['node'] = Node()
        return _info['node']
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
