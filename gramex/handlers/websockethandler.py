from collections import OrderedDict
from urllib.parse import urlparse
from gramex.transforms import build_transform
from .basehandler import BaseWebSocketHandler


class WebSocketHandler(BaseWebSocketHandler):
    '''
    Handles WebSockets. It accepts these parameters:

    :arg function open: ``open(handler)`` is called when the connection is opened
    :arg function on_message: ``on_message(handler, message)`` is called with a
        string message when the client sends a message.
    :arg function on_close: ``on_close(handler)`` is called when the websocket is
        closed.
    :arg list origins: a domain name or list of domain names. No wildcards

    The handler has a ``.write_message(text)`` method that sends a message back
    to the client.
    '''
    @staticmethod
    def _setup(cls, **kwargs):
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
                setattr(cls, method, build_transform(
                    kwargs[method],
                    vars=OrderedDict((arg, None) for arg in override_methods[method]),
                    filename='url:%s.%s' % (cls.name, method)))

    @classmethod
    def setup(cls, **kwargs):
        super(WebSocketHandler, cls).setup(**kwargs)
        cls._setup(cls, **kwargs)

    def check_origin(self, origin):
        origins = self.kwargs.get('origins', [])
        if not origins:
            return True
        if isinstance(origins, (str, bytes)):
            origins = [origins]
        domain = urlparse(origin).netloc
        for allowed_origin in origins:
            if domain.endswith(allowed_origin):
                return True
        return False
