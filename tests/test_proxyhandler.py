import requests
from gramex.http import METHOD_NOT_ALLOWED
from . import TestGramex


class TestProxyHandler(TestGramex):
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
