from gramex.transforms import build_transform
from .basehandler import BaseWebSocketHandler


class WebSocketHandler(BaseWebSocketHandler):
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
