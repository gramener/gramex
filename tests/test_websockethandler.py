from __future__ import unicode_literals

import time
from requests import Request
from .test_auth import AuthBase
from nose.tools import eq_
from .server import base_url
from websocket import create_connection, WebSocketException
from gramex.http import UNAUTHORIZED, FORBIDDEN
from requests.cookies import get_cookie_header


class TestWebSocketHandler(AuthBase):
    delay = 0.01

    @classmethod
    def setUpClass(cls):
        cls.message = 'Hello'
        AuthBase.setUpClass()
        cls.url = base_url + '/auth/simple'

    def test_events(self):
        self.check('/ws/info')
        for count in range(1, 10):
            msg = '{:s}: {:d}'.format(self.message, count)
            ws = create_connection(base_url.replace('http://', 'ws://') + '/ws/socket')
            ws.send(msg)
            ws.close()
            time.sleep(self.delay)
            eq_(self.check('/ws/info').json(), [
                {'method': 'open'},
                {'method': 'on_message', 'message': msg},
                {'method': 'on_close'}
            ])

    def test_unauthorised(self):
        try:
            create_connection(base_url.replace('http://', 'ws://') + '/ws/auth')
        except WebSocketException as exc:
            self.assertEqual(exc.status_code, UNAUTHORIZED)
        else:
            self.fail('Websocket allows access without login')

    def test_forbidden(self):
        self.login('beta', 'beta')
        try:
            create_connection(base_url.replace('http://', 'ws://') + '/ws/auth', header=[
                'Cookie: {}'.format(get_cookie_header(self.session.cookies, Request(url=base_url)))
            ])
        except WebSocketException as exc:
            self.assertEqual(exc.status_code, FORBIDDEN)
        else:
            self.fail('Websocket allows access for unallowed user')

    def test_authorised_user(self):
        # Log in as user alpha. Authorised users should get access.
        self.login('alpha', 'alpha')
        ws = create_connection(base_url.replace('http://', 'ws://') + '/ws/auth', header=[
            'Cookie: {}'.format(get_cookie_header(self.session.cookies, Request(url=base_url)))
        ])
        ws.send(self.message)
        ws.close()
        time.sleep(self.delay)
        eq_(self.check('/ws/info').json(), [
            {'method': 'open'},
            {'method': 'on_message', 'message': self.message},
            {'method': 'on_close'}
        ])
