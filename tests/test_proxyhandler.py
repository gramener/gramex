import requests
from gramex.http import METHOD_NOT_ALLOWED, UNAUTHORIZED, FORBIDDEN
from .test_auth import AuthBase
from .server import base_url
from websocket import create_connection, WebSocketException
import time
from nose.tools import eq_
from requests import Request
from requests.cookies import get_cookie_header


class TestProxyHandler(AuthBase):
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
            ws = create_connection(base_url.replace('http://', 'ws://') + '/ws-proxy/socket/')
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
            create_connection(base_url.replace('http://', 'ws://') + '/ws-proxy/auth/')
        except WebSocketException as exc:
            self.assertEqual(exc.status_code, UNAUTHORIZED)
        else:
            self.fail('Websocket allows access without login')

    def test_forbidden(self):
        self.login('beta', 'beta')
        try:
            create_connection(base_url.replace('http://', 'ws://') + '/ws-proxy/auth/', header=[
                'Cookie: {}'.format(get_cookie_header(self.session.cookies, Request(url=base_url)))
            ])
        except WebSocketException as exc:
            self.assertEqual(exc.status_code, FORBIDDEN)
        else:
            self.fail('Websocket allows access for unallowed user')

    def test_authorised_user(self):
        # Log in as user alpha. Authorised users should get access.
        self.login('alpha', 'alpha')
        ws = create_connection(base_url.replace('http://', 'ws://') + '/ws-proxy/auth/', header=[
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

    def test_proxyhandler(self):
        session = requests.Session()
        r = self.check('/auth/session', session=session)
        session_id = r.json()['id']
        r = self.check('/xsrf', session=session)
        xsrf_token = r.cookies['_xsrf']

        for method in ['get', 'post', 'put']:
            request_headers = {}
            if method != 'get':
                request_headers['X-Xsrftoken'] = xsrf_token
            r = self.check(
                '/proxy/httpbin/?a=1&z=5',
                session=session,
                method=method,
                request_headers=request_headers,
                headers={
                    # modify: adds the request method as a header
                    'X-Modify': method.upper(),
                    # headers: adds a custom HTTP header
                    'X-Proxy-Custom': 'custom-header',
                })
            # ProxyHandler returns the actual URL mapped
            self.assertIn('X-Proxy-Url', r.headers)
            result = r.json()
            self.assertDictContainsSubset({
                # request_headers: true translates to the passed value
                'User-Agent': 'python-requests/' + requests.__version__,
                # request_headers: value passed to the target
                'X-From': 'ProxyHandler',
                # request_headers: value formatted with handler
                'Session': 'Session ' + session_id,
                # prepare: adds HTTP headers
                'X-Prepare': method.upper(),
            }, result['headers'], )
            self.assertEquals({
                # default: keys are passed as args
                'y': ['1', '2'],
                # URL arguments are also applied
                'x': ['1', '2'],
                # Proxy request args are passed
                'a': ['1'],
                # Proxy request args over-rides default: value and URL value
                'z': ['5'],
                # prepare: can modify request arguments
                'b': ['1'],
            }, result['args'])

        # PATCH method does not work because /httpbin does not support it
        r = self.check('/proxy/httpbin/', session=session, method='patch',
                       request_headers={'X-Xsrftoken': xsrf_token},
                       code=METHOD_NOT_ALLOWED,
                       headers={
                           'X-Proxy-Url': True,
                           'X-Proxy-Custom': 'custom-header',
                           'X-Modify': 'PATCH',
                       })

        # DELETE method does not work because /proxy/httpbin/ does not support it
        r = self.check('/proxy/httpbin/', method='delete', session=session,
                       request_headers={'X-Xsrftoken': xsrf_token},
                       code=METHOD_NOT_ALLOWED,
                       headers={
                           'X-Proxy-Url': False,
                           'X-Proxy-Custom': False,
                           'X-Modify': False,
                       })

        # URL pattern wildcards
        result = self.check('/proxy/httpbinprefix/suffix', session=session).json()
        self.assertEquals({
            'pre': ['prefix'],      # path_args from the url requested
            'post': ['suffix'],     # path_args from the url requested
            'y': ['1', '2'],        # from default:
            'x': ['1', '2'],        # from url:
            'z': ['1'],             # from url:
            'b': ['1'],             # from prepare:
        }, result['args'])
