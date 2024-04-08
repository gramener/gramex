import tornado.web
import tornado.gen
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from tornado.httputil import HTTPHeaders, parse_response_start_line, HTTPInputError
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from typing import Callable
from gramex.transforms import build_transform
from gramex.config import app_log
from gramex.http import MOVED_PERMANENTLY, FOUND
from .basehandler import BaseWebSocketHandler, BaseHandler
from gramex.handlers import WebSocketHandler


skip_response_headers = {
    'Connection',
    'Content-Encoding',
    'Content-Length',
    'Host',
    'Transfer-Encoding',
}


class ProxyHandler(BaseHandler, BaseWebSocketHandler):
    @classmethod
    def setup(
        cls,
        url: str,
        request_headers: dict = {},
        default: dict = {},
        prepare: Callable = None,
        modify: Callable = None,
        headers: dict = {},
        connect_timeout: int = 20,
        request_timeout: int = 20,
        **kwargs,
    ):
        '''
        Passes the request to another HTTP REST API endpoint and returns its
        response. This is useful when:

        - exposing another website but via Gramex authentication (e.g. R-Shiny apps)
        - a server-side REST API must be accessed via the browser (e.g. Twitter)
        - passing requests to an API that requires authentication (e.g. Google)
        - the request or response needs to be transformed (e.g. add sentiment)
        - caching is required on the API (e.g. cache for 10 min)

        Parameters:

            url: URL endpoint to forward to. If the pattern ends with
                `(.*)`, that part is added to this url.
            request_headers: HTTP headers to be passed to the url.
                - `"*": true` forwards all HTTP headers from the request as-is.
                - A value of `true` forwards this header from the request as-is.
                - Any string value is formatted with `handler` as a variable.
            default: Default URL query parameters
            headers: HTTP headers to set on the response
            prepare: A function that accepts any of `handler` and `request`
                (a tornado.httpclient.HTTPRequest) and modifies the `request` in-place
            modify: A function that accepts any of `handler`, `request`
                and `response` (tornado.httpclient.HTTPResponse) and modifies the
                `response` in-place
            connect_timeout: Timeout for initial connection in seconds (default: 20)
            request_timeout: Timeout for entire request in seconds (default: 20)
            stream: If True, the response is streamed (default: false)

        The response has the same HTTP headers and body as the proxied request, but:

        - Connection and Transfer-Encoding headers are ignored
        - `X-Proxy-Url:` header has the final URL that responded (after redirects)

        These headers can be over-ridden by the `headers:` section.

        ```yaml
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
        ```
        '''
        super(ProxyHandler, cls).setup(**kwargs)
        WebSocketHandler._setup(cls, **kwargs)
        cls.url, cls.request_headers, cls.default = url, request_headers, default
        cls.headers = headers
        cls.connect_timeout, cls.request_timeout = connect_timeout, request_timeout
        cls.info = {'stream': kwargs.get('stream', False)}
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
        if 'stream' in self.info:
            request.header_callback = self._header_callback
            request.streaming_callback = self._write_and_flush

        if 'prepare' in self.info:
            self.info['prepare'](handler=self, request=request, response=None)

        app_log.debug(f'{self.name}: proxying {url}')
        response = yield self.browser().fetch(request, raise_error=False)

        # Set response headers only if not streaming
        if not self.info['stream']:
            if response.code in (MOVED_PERMANENTLY, FOUND):
                location = response.headers.get('Location', '')
                # TODO: check if Location: header MATCHES the url, not startswith
                # url: example.org/?x should match Location: example.org/?a=1&x
                # even though location does not start with url.
                if location.startswith(url):
                    response.headers['Location'] = location.replace('url', self.conf.pattern)
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
        if 'modify' in self.info:
            self.info['modify'](handler=self, request=request, response=response)

        if response.body is not None:
            self._write_and_flush(response.body)

    def _write_and_flush(self, data: bytes):
        '''Write data to response and flush it'''
        self.write(data)
        self.flush()

    def _header_callback(self, header_line: str):
        '''Proxy request headers as they appear'''
        # If we don't use a _header_callback, streaming writes will write default headers
        # before we get a chance to set the headers. So set them as soon as they appear
        # From tornado.curl_httpclient.CurlAsyncHTTPClient._curl_header_callback
        header_line = header_line.rstrip()
        if header_line.startswith('HTTP/'):
            try:
                (__, code, reason) = parse_response_start_line(header_line)
                self.set_status(code, reason)
            except HTTPInputError:
                return
        elif header_line:
            # from tornado.httputil.HTTPHeaders.parse_line. Ignore multi-line headers
            try:
                name, value = header_line.split(':', 1)
                if name not in skip_response_headers:
                    self.set_header(name, value)
            except ValueError as err:
                raise HTTPInputError('no colon in header line') from err
