import json
import time
from gramex.config import CustomJSONEncoder
from .websockethandler import WebSocketHandler
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

    def on_message(self, message: Union[str, bytes]) -> Optional[Awaitable[None]]:
        import pandas as pd
        import gramex.data
        from base64 import urlsafe_b64encode
        from blinker import signal
        from uuid import uuid4

        # TODO from gramex.services import get_mailer

        # Store in database
        message = json.loads(message)
        args = {k: [v] for k, v in message['data'].items()}
        args['id'] = [urlsafe_b64encode(uuid4().bytes).strip(b"=").decode('utf-8')]
        args['user'] = [self.current_user.get('id', None) if self.current_user else None]
        args['timestamp'] = [time.time()]
        if message['type'] == 'post':
            gramex.data.insert(**self.data, args=args)
        elif message['type'] == 'delete':
            gramex.data.delete(**self.data, args=args)
        elif message['type'] == 'put':
            gramex.data.update(**self.data, args=args)

        # Send email asynchronously
        # TODO mailer = get_mailer(self.email)

        # Send message to all clients
        signal(self.name).send(pd.DataFrame(args))

        # TODO: Handle errors

    def write_data(self, *args, **kwargs):
        '''Send message to client if it matches the filter arguments'''
        import gramex.data

        for _index, row in gramex.data.filter(*args, **kwargs, args=self.args).iterrows():
            self.write_message(json.dumps(row, cls=CustomJSONEncoder))
