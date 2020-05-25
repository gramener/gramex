'''
Python Node.js bridge
'''
import os
import re
import json
from shutilwhich import which
from tornado.gen import coroutine, Return, sleep
from tornado.websocket import websocket_connect, WebSocketClosedError
from gramex.config import variables
from gramex.cache import daemon
from gramex.config import app_log


class Node(object):
    '''
    Usage::

        node = Node(port=9966, node_path='/tmp/')
        total = await node.js('return {"total": x + y}', x='a', y=10)['total']
    '''
    _path = os.path.join(variables['GRAMEXAPPS'], 'pynode', 'index.js')
    _delay = 0.01

    def __init__(self, port=9966, cwd=None, node_path=None, timeout=10):
        self.port = port
        self.cwd = cwd
        self.node_path = node_path
        self.url = 'ws://localhost:%s' % port
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
                # TODO: node_path
                self.proc = yield daemon(
                    [which('node'), self._path, '--port=%s' % self.port],
                    first_line=re.compile(r'pynode: 1.\d+.\d+ port: %s' % self.port),
                    cwd=self.cwd,
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
            self.conn = None
            raise
        # Receive the response.
        # Note: read_message() cannot be called again while a request is running.
        # (Yes, that's odd. Maybe Anand is missing something.)
        # So wait until the read_future is cleared.
        while getattr(self.conn, 'read_future', None) is not None:
            yield sleep(self._delay)
        msg = yield self.conn.read_message()
        # If node has died, clear the connection to restart it.
        if msg is None:
            self.conn = None
            raise WebSocketClosedError()

        # Parse the result as JSON. Log errors if any
        result = json.loads(msg)
        if result['error']:
            app_log.error(result['error']['stack'])
        raise Return(result)


# Create an instance for normal usage.
node = Node()
