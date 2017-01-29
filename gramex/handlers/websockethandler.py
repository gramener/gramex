from six import string_types
from six.moves.urllib_parse import urlparse
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
    @classmethod
    def setup(cls, **kwargs):
        super(WebSocketHandler, cls).setup(**kwargs)
        override_methods = {
            'open': {'handler': None},
            'on_message': {'handler': None, 'message': None},
            'on_close': {'handler': None},
            'on_pong': {'handler': None, 'data': None},
            'select_subprotocol': {'handler': None, 'subprotocols': None},
            'get_compression_options': {'handler': None},
        }
        for method in override_methods:
            if method in kwargs:
                setattr(cls, method, build_transform(
                    kwargs[method], vars=override_methods[method],
                    filename='url:%s.%s' % (cls.name, method)))

    def check_origin(self, origin):
        origins = self.kwargs.get('origins', [])
        if not origins:
            return True
        if isinstance(origins, string_types):
            origins = [origins]
        domain = urlparse(origin).netloc
        for allowed_origin in origins:
            if domain.netloc.endswith(allowed_origin):
                return True
        return False
