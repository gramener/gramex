import json
from collections import defaultdict
from .basehandler import BaseWebSocketHandler
from gramex.transforms import build_transform
from tornado.concurrent import Future
from tornado.gen import coroutine
from typing import List, Dict, Any, Union, Optional, Awaitable, Callable


class MessageHandler(BaseWebSocketHandler):
    '''A WebSocketHandler that sends and receives comments.

    Configuration:

    ```yaml
        handler: MessageHandler
        kwargs:
          data:
            url: sqlite:///$YAMLPATH/comments.db
            table: comments
            columns:
              subject: TEXT
          alert:
            service: gramex-guide-mailer
            to: ...
          prepare: msg.update('x', 1)
          modify: msg.update('to', 'admin@example.org')
    ```
    '''

    function_vars = {
        'open': {'args': None, 'handler': None},
        'prepare': {'msg': None, 'handler': None},
        'modify': {'msg': None, 'handler': None},
    }

    @classmethod
    def setup(
        cls,
        open: Union[Callable, str, None] = None,
        prepare: Union[Callable, str, None] = None,
        modify: Union[Callable, str, None] = None,
        message_default: Dict[str, Dict[str, Any]] = None,
        alert: Union[Dict, None] = None,
        **kwargs,
    ):
        from gramex.config import merge

        super(BaseWebSocketHandler, cls).setup(**kwargs)
        # Ensure data has id, and data.columns has id, user, timestamp. Default type is text
        cls.data = cls.clear_special_keys(kwargs)
        cls.data['id'] = 'id'
        merge(
            cls.data.setdefault('columns', {}),
            {'id': {'type': 'text', 'primary_key': True}, 'user': 'text', 'timestamp': 'text'},
            mode='setdefault',
        )
        cls.alert = alert or {'methods': []}
        cls.info = {'open': open, 'prepare': prepare, 'modify': modify}
        cls.setup_message_default(message_default)
        for key, fn in cls.info.items():
            if fn:
                cls.info[key] = build_transform(
                    {'function': fn}, filename=f'url:{cls.name}.{key}', vars=cls.function_vars[key]
                )

    def open(self):
        import gramex.data
        from blinker import signal

        self._method_map = {
            'POST': gramex.data.insert,
            'PUT': gramex.data.update,
            'DELETE': gramex.data.delete,
        }
        if callable(self.info['open']):
            self.info['open'](self.args, self)
        signal(self.name).connect(self.write_data)
        self.write_data(**self.data)

    def on_close(self):
        from blinker import signal

        signal(self.name).disconnect(self.write_data)

    @coroutine
    def on_message(self, message: Union[str, bytes]) -> Optional[Awaitable[None]]:
        import pandas as pd
        from blinker import signal
        from gramex import service
        from gramex.services import create_mail, get_mailer

        msg = json.loads(message)
        if not isinstance(msg, dict):
            raise ValueError(f'url:{self.name}: message not a dict: {msg}')
        method = msg['_method'] = msg.get('_method', 'POST').upper()
        if method not in self._method_map:
            raise ValueError(f'url:{self.name}: invalid _method: {method}')
        for key, default_fn in self._message_default.get(method, {}).items():
            msg[key] = default_fn(msg=msg, handler=self)

        # Call prepare before updating the database
        if callable(self.info['prepare']):
            self.info['prepare'](msg=msg, handler=self)

        args = {k: [v] for k, v in msg.items()}
        yield service.threadpool.submit(self._method_map[method], **self.data, args=args)

        # Call modify after updating the database
        if callable(self.info['modify']):
            self.info['modify'](msg=msg, handler=self)

        # Send msg to all clients
        signal(self.name).send(pd.DataFrame(args))

        # Send alert for specified methods and if message does not disallow alert
        if method in self.alert.get('methods', ['POST']) and msg.get('_alert', True):
            _services, mailer = get_mailer(self.alert, self.name)
            # Do NOT yield this future. Just call and forget it. Else future messages are queued.
            # mail_log() ensures that exceptions are logged.
            service.threadpool.submit(mailer.mail_log, **create_mail(msg, self.alert, self.name))

    def write_data(self, *args, **kwargs) -> List[Future]:
        '''Filter dataframe/url on arguments and send each row to client'''
        from gramex.config import CustomJSONEncoder
        import gramex.data

        futures = []
        # TODO: Careful! For DELETE, columns may not have the expected values
        for _index, row in gramex.data.filter(*args, **kwargs, args=self.args).iterrows():
            futures.append(self.write_message(json.dumps(row, cls=CustomJSONEncoder)))
        return futures

    @classmethod
    def setup_message_default(cls, message_default):
        '''Set up self._message_default as a method (POST/PUT) -> key -> value fn mapping.

        method:default is a dict like this:

        ```yaml
            message_default:
                POST:
                    user: handler.current_user.id if handler.current_user else None
                    timestamp: datetime.datetime.utcnow().isoformat()
                PUT:
                    timestamp: datetime.datetime.utcnow().isoformat()
        ```

        This creates a self._message_default dict with method (uppercase) keys, and values as
        key-value functions.

        ```python
            self._message_default = {
                'POST': {
                    'user': lambda args, handler: handler.current_user.id if handler...,
                    'timestamp': lambda args, handler: datetime.datetime.utcnow()...,
                },
                'PUT': {
                    'timestamp': lambda args, handler: datetime.datetime.utcnow()...,
                }
            }
        ```

        To apply the default, pick the relevant method. Assign keys the result of functions
        passing (msg, self).
        '''
        cls._message_default = defaultdict(dict)
        if message_default is None:
            return
        if not isinstance(message_default, dict):
            raise ValueError(f'url:{cls.name}.message_default must be dict not {message_default}')
        for method, defaults in message_default.items():
            for key, fn in defaults.items():
                cls._message_default[method.upper()][key] = build_transform(
                    {'function': fn},
                    filename=f'url:{cls.name}.message_default.{method}',
                    vars={'msg': None, 'handler': None},
                    iter=False,
                )
