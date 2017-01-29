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
            'check_origin': {'handler': None, 'origin': None},
        }
        for method in override_methods:
            if method in kwargs:
                setattr(cls, method, build_transform(
                    kwargs[method], vars=override_methods[method],
                    filename='url:%s.%s' % (cls.name, method)))
