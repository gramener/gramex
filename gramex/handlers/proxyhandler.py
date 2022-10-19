import tornado.web
import tornado.gen
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from tornado.httputil import HTTPHeaders
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from gramex.transforms import build_transform
from gramex.config import app_log
from gramex.http import MOVED_PERMANENTLY, FOUND
from .basehandler import BaseWebSocketHandler, BaseHandler
from gramex.handlers import WebSocketHandler


class ProxyHandler(BaseHandler, BaseWebSocketHandler):
    '''
    Passes the request to another HTTP REST API endpoint and returns its
    response. This is useful when:

    - exposing another website but via Gramex authentication (e.g. R-Shiny apps)
    - a server-side REST API must be accessed via the browser (e.g. Twitter)
    - passing requests to an API that requires authentication (e.g. Google)
    - the request or response needs to be transformed (e.g. add sentiment)
    - caching is required on the API (e.g. cache for 10 min)

    :arg string url: URL endpoint to forward to. If the pattern ends with
        ``(.*)``, that part is added to this url.
    :arg dict request_headers: HTTP headers to be passed to the url.
        - ``"*": true`` forwards all HTTP headers from the request as-is.
        - A value of ``true`` forwards this header from the request as-is.
        - Any string value is formatted with ``handler`` as a variable.
    :arg dict default: Default URL query parameters
    :arg dict headers: HTTP headers to set on the response
    :arg function prepare: A function that accepts any of ``handler`` and ``request``
        (a tornado.httpclient.HTTPRequest) and modifies the ``request`` in-place
    :arg function modify: A function that accepts any of ``handler``, ``request``
        and ``response`` (tornado.httpclient.HTTPResponse) and modifies the
        ``response`` in-place
    :arg int connect_timeout: Timeout for initial connection in seconds (default: 20)
    :arg int request_timeout: Timeout for entire request in seconds (default: 20)

    Example YAML configuration::

        pattern: /gmail/(.*)
        handler: ProxyHandler
        kwargs:
            url: https://www.googleapis.com/gmail/v1/
            request_headers:
                "*": true           # Pass on all HTTP headers
                Cookie: true        # Pass on the Cookie HTTP header
                # Over-ride the Authorization header
                Authorization: 'Bearer {handler.session[google_access_token]}'
            default:
                alt: json

    The response has the same HTTP headers and body as the proxied request, but:

    - Connection and Transfer-Encoding headers are ignored
    - ``X-Proxy-Url:`` header has the final URL that responded (after redirects)

    These headers can be over-ridden by the ``headers:`` section.
    '''

    @classmethod
    def setup(
        cls,
        url,
        request_headers={},
        default={},
        prepare=None,
        modify=None,
        headers={},
        connect_timeout=20,
        request_timeout=20,
        **kwargs,
    ):
        super(ProxyHandler, cls).setup(**kwargs)
        WebSocketHandler._setup(cls, **kwargs)
        cls.url, cls.request_headers, cls.default = url, request_headers, default
        cls.headers = headers
        cls.connect_timeout, cls.request_timeout = connect_timeout, request_timeout
        cls.info = {}
        for key, fn in (('prepare', prepare), ('modify', modify)):
            if fn:
                cls.info[key] = build_transform(
                    {'function': fn},
                    filename=f'url:{cls.name}.{key}',
                    vars={'handler': None, 'request': None, 'response': None},
                )
        cls.post = cls.put = cls.delete = cls.patch = cls.get
        if not kwargs.get('cors'):
            cls.options = cls.get

    def browser(self):
        # Create the browser when required. Don't create it in setup(), because:
        #   gramex.services.init() calls setup() from a thread, and
        #   AsyncHTTPClient can't be created from a thread
        if not hasattr(self, '_browser'):
            self._browser = AsyncHTTPClient()
        return self._browser

    def authorize(self, *args, **kwargs):
        if self.request.headers.get('Upgrade', '') == 'websocket':
            WebSocketHandler.authorize(self)
        else:
            super(ProxyHandler, self).authorize()

    @tornado.gen.coroutine
    def get(self, *path_args):
        ws = self.request.headers.get('Upgrade', '') == 'websocket'
        if ws:
            return WebSocketHandler.get(self)
        # Construct HTTP headers
        headers = HTTPHeaders(self.request.headers if self.request_headers.get('*', None) else {})
        for key, val in self.request_headers.items():
            if key == '*':
                continue
            if val is True:
                if key in self.request.headers:
                    headers[key] = self.request.headers[key]
            else:
                headers[key] = str(val).format(handler=self)

        # Update query parameters
        # TODO: use a named capture for path_args? This is not the right method
        parts = urlsplit(self.url.format(*path_args))
        params = {
            key: (
                [str(v).format(handler=self) for v in val]
                if isinstance(val, list)
                else str(val).format(handler=self)
            )
            for key, val in self.default.items()
        }
        params.update(parse_qs(parts.query))
        params.update(self.args)
        query = urlencode(params, doseq=True)
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))

        request = HTTPRequest(
            url=url,
            method=self.request.method,
            headers=headers,
            body=None if self.request.method == 'GET' else self.request.body,
            connect_timeout=self.connect_timeout,
            request_timeout=self.request_timeout,
        )

        if 'prepare' in self.info:
            self.info['prepare'](handler=self, request=request, response=None)

        app_log.debug(f'{self.name}: proxying {url}')
        response = yield self.browser().fetch(request, raise_error=False)

        if response.code in (MOVED_PERMANENTLY, FOUND):
            location = response.headers.get('Location', '')
            # TODO: check if Location: header MATCHES the url, not startswith
            # url: example.org/?x should match Location: example.org/?a=1&x
            # even though location does not start with url.
            if location.startswith(url):
                response.headers['Location'] = location.replace('url', self.conf.pattern)

        if 'modify' in self.info:
            self.info['modify'](handler=self, request=request, response=response)

        # Pass on the headers as-is, but override with the handler HTTP headers
        self.set_header('X-Proxy-Url', response.effective_url)
        for header_name, header_value in response.headers.items():
            if header_name not in {'Connection', 'Transfer-Encoding', 'Content-Length'}:
                self.set_header(header_name, header_value)
        # Proxies may send the wrong Content-Length. Correct it, else Tornado raises an error
        if response.body is not None:
            self.set_header('Content-Length', len(response.body))
        for header_name, header_value in self.headers.items():
            self.set_header(header_name, header_value)
        # Pass on HTTP status code and response body as-is
        self.set_status(response.code, reason=response.reason)
        if response.body is not None:
            self.write(response.body)
