from __future__ import unicode_literals

import json
from nose.tools import eq_
from server import base_url
from websocket import create_connection
from . import TestGramex


class TestWebSocketHandler(TestGramex):
    'Test WebSocketHandler'

    def test_connection(self):
        # Clear the websocket log
        self.check('/ws/info')

        message = 'Hello'
        ws = create_connection(base_url.replace('http://', 'ws://') + '/ws/socket')
        ws.send(message)
        ws.close()

        response = self.check('/ws/info')
        eq_(json.loads(response.text), [
          {'method': 'open'},
          {'method': 'on_message', 'message': message},
          {'method': 'on_close'},
        ])
