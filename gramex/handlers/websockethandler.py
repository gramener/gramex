from urllib.parse import urlparse
from gramex.transforms import build_transform
from .basehandler import BaseWebSocketHandler


class WebSocketHandler(BaseWebSocketHandler):
    '''Creates a websocket microservice.

    - `open`: function. `open(handler)` is called when the connection is opened
    - `on_message`: function. `on_message(handler, message: str)` is called when client sends a
        message
    - `on_close`: function. `on_close(handler)` is called when connection is closed.
    - `origins`: a domain name or list of domain names. No wildcards

    Functions can use `handler.write_message(msg: str)` to sends a message back to the client.
    '''

    @classmethod
    def setup(cls, **kwargs):
        super(WebSocketHandler, cls).setup(**kwargs)
        cls._setup(cls, **kwargs)

    @staticmethod
    def _setup(cls, **kwargs):
        # ProxyHandler proxies websockets, and needs a setup without subclassing WebSocketHandler.
        # _setup() can be used both by WebSocketHandler and ProxyHandler.
        override_methods = {
            'open': ['handler'],
            'on_message': ['handler', 'message'],
            'on_close': ['handler'],
            'on_pong': ['handler', 'data'],
            'select_subprotocol': ['handler', 'subprotocols'],
            'get_compression_options': ['handler'],
        }
        for method in override_methods:
            if method in kwargs:
                setattr(
                    cls,
                    method,
                    build_transform(
                        kwargs[method],
                        vars={arg: None for arg in override_methods[method]},
                        filename=f'url:{cls.name}.{method}',
                        iter=False,
                    ),
                )

    def check_origin(self, origin):
        origins = self.kwargs.get('origins', [])
        if not origins:
            return True
        if isinstance(origins, (str, bytes)):
            origins = [origins]
        domain = urlparse(origin).netloc
        return any(domain.endswith(allowed_origin) for allowed_origin in origins)
