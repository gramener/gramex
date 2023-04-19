import json
import time
from .websockethandler import WebSocketHandler
from gramex.config import CustomJSONEncoder
from tornado.gen import coroutine
from typing import Dict, Any, Union, Optional, Awaitable


class CommentHandler(WebSocketHandler):
    '''A WebSocketHandler that sends and receives comments.

    Configuration:

        handler: CommentHandler
        kwargs:
          data:
            url: sqlite:///$YAMLPATH/comments.db
            table: comments
            columns:
              message: TEXT
          email:
            service: gramex-guide-mailer
            to: ...
          # TODO: Allow plugins
    '''

    @classmethod
    def setup(cls, data: Dict[str, Any], email: Union[str, None] = None, **kwargs):
        super(WebSocketHandler, cls).setup(**kwargs)
        cls.data = data
        cls.email = email
        # Ensure data.columns has id, user, timestamp
        data['id'] = 'id'
        cols = data.get('columns', {})
        cols.setdefault('id', 'text')
        cols.setdefault('user', 'text')
        cols.setdefault('timestamp', 'float')

    def open(self):
        import gramex.data
        from blinker import signal

        signal(self.name).connect(self.write_data)
        self.write_data(gramex.data.filter(**self.data, args=self.args))

    def on_close(self):
        from blinker import signal

        signal(self.name).disconnect(self.write_data)

    @coroutine
    def on_message(self, message: Union[str, bytes]) -> Optional[Awaitable[None]]:
        import pandas as pd
        import gramex.data
        from gramex import service
        from gramex.services import create_mail, get_mailer
        from base64 import urlsafe_b64encode
        from blinker import signal
        from uuid import uuid4

        message = json.loads(message)
        # TODO: plugins
        # TODO: Restrict usage by user -- handler.current_user must match something
        # Store in database
        method = message.setdefault('_method', 'post')
        args = {k: [v] for k, v in message.items() if k != '_method'}
        if method == 'post':
            args['user'] = [self.current_user.get('id', None) if self.current_user else None]
            args['timestamp'] = [time.time()]
            args['id'] = [urlsafe_b64encode(uuid4().bytes).strip(b"=").decode('utf-8')]
            gramex.data.insert(**self.data, args=args)
        elif method == 'delete':
            gramex.data.delete(**self.data, args={"id": [message["id"]]})
        elif method == 'put':
            updated_msg = {k: [v] for k, v in message['data'].items()}
            gramex.data.update(**self.data, args=updated_msg)

        if self.email and method in self.email.get('methods', ['post']):
            # Send message to all clients
            signal(self.name).send(pd.DataFrame(args))
            # Send email
            if self.email:
                _services, mailer = get_mailer(self.email, self.name)
                msg = create_mail({k: v[0] for k, v in args.items()}, self.email, self.name)
                service.threadpool.submit(mailer.mail, **msg)

        # TODO: Handle errors

    def write_data(self, *args, **kwargs):
        '''Send message to client if it matches the filter arguments'''
        import gramex.data

        for _index, row in gramex.data.filter(*args, **kwargs, args=self.args).iterrows():
            self.write_message(json.dumps(row, cls=CustomJSONEncoder))
