import json
from .basehandler import BaseWebSocketHandler
from gramex.transforms import build_transform
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient
from typing import Callable, Dict, Union


class ChatGPTHandler(BaseWebSocketHandler):
    '''A WebSocketHandler that proxies requests to OpenAI chat completions.

    Configuration:

    ```yaml
        handler: ChatGPTHandler
        kwargs:
          key: ...
          max_history: ...
          model: gpt-3.5-turbo
          temperature:
              function: handler.args.get('temperature', 0.9)
          ...
    ```
    '''

    _transform_vars = {
        'open': {'params': None, 'handler': None},
        'prepare': {'message': None, 'handler': None},
        'modify': {'data': None, 'handler': None},
    }
    _api_conf_defaults = {
        'url': 'https://api.openai.com/v1/chat/completions',
        'key': None,
        'max_history': None,
    }
    _params_defaults = {
        'model': 'gpt-3.5-turbo',
        'temperature': None,
        'top_p': None,
        'n': None,
        'stream': {'function': '"stream" in handler.args'},
        'stop': None,
        'max_tokens': None,
        'frequency_penalty': None,
        'presence_penalty': None,
        'logit_bias': None,
        'user': None,
    }

    @classmethod
    def setup(cls, **kwargs):
        super(BaseWebSocketHandler, cls).setup(**kwargs)

        cls._api_conf, cls._params, cls._transform = {}, {}, {}
        # url, key, max_history can be set as key: xxx or key: {function: handler.args.get('key')}
        for k, v in cls._api_conf_defaults.items():
            cls._set_default(k, kwargs.pop(k, v), lambda x: cls._api_conf.update({k: x}))
        # All API params can be set as as key: xxx or key: {function: handler.args.get('key')}
        for k, v in cls._params_defaults.items():
            cls._set_default(k, kwargs.pop(k, v), lambda x: cls._params.update({k: x}))
        # open, prepare and modify are specified directly as the functions
        for k, vars in cls._transform_vars.items():
            v = {'function': kwargs[k]} if k in kwargs else ''
            cls._set_default(k, v, lambda x: cls._transform.update({k: x}), vars=vars)

    @classmethod
    def _set_default(
        cls,
        k: str,
        v: Union[int, str, Callable, Dict[str, str]],
        setter: Callable,
        vars: Dict = {'handler': None},
    ):
        if isinstance(v, dict) and 'function' in v:
            v = build_transform(v, filename=f'url:{cls.name}.{k}', vars=vars, iter=False)
        if v is not None:
            setter(v)

    def open(self):
        self.http = AsyncHTTPClient()
        self.api_conf = {k: v(self) if callable(v) else v for k, v in self._api_conf.items()}
        self.params = {k: v(self) if callable(v) else v for k, v in self._params.items()}
        self.params.setdefault('messages', [])
        self.headers = {'Content-Type': 'application/json'}
        if 'key' in self.api_conf:
            self.headers['Authorization'] = f'Bearer {self.api_conf.get("key", "")}'
        if callable(self._transform['open']):
            self._transform['open'](self.params, self)

    @coroutine
    def on_message(self, message: str):
        if 'max_history' in self.api_conf:
            max_history = self.api_conf['max_history']
            self.params['messages'] = self.params['messages'][-max_history * 2 :]

        if callable(self._transform['prepare']):
            result = self._transform['prepare'](message=message, handler=self)
            if result is not None:
                message = result
        self.params['messages'].append({'role': 'user', 'content': message})

        kwargs = {}
        if self.params['stream']:
            kwargs['streaming_callback'] = self.on_chunk
            self.chunks, self.tokens = [], []
        try:
            r = yield self.http.fetch(
                self.api_conf['url'],
                method='POST',
                request_timeout=0,  # no timeout
                body=json.dumps(self.params),
                headers=self.headers,
                raise_error=False,
                **kwargs,
            )
        except Exception as e:  # noqa - catch all exceptions
            # If there's a non-HTTP error (e.g. timeout), return it
            self.write_message(f'[ERROR] {e}')
            self.write_message('')
            return
        # If there's a HTTP error, return it
        if r.code != 200:
            error = json.loads(r.body or b''.join(self.chunks))['error']
            self.write_message('[ERROR]\n' + '\n'.join(f'{k}: {v}' for k, v in error.items()))
            self.write_message('')
        # If streaming is enabled, ignore the empty r.body. self.on_chunk will handle it
        # If streaming is disabled, return the entire response
        elif r.body:
            data = json.loads(r.body)
            # TODO: Handle multiple responses in data['choices'], i.e. n > 1, properly
            content = data['choices'][0]['message']['content']
            # Call modify(data). Use the return value (if any) as the content
            if callable(self._transform['modify']):
                result = self._transform['modify'](data=data, handler=self)
                if result is not None:
                    content = result
            self.params['messages'].append({'role': 'assistant', 'content': content})
            self.write_message(content)
            self.write_message('')

    def on_chunk(self, chunk: bytes):
        self.chunks.append(chunk.decode('utf-8'))
        [*lines, remaining] = ''.join(self.chunks).split('\n\n')
        self.chunks = [remaining]
        # Each chunk has a data: ... but the last chunk has an additional line with
        # data: [DONE]. We ignore that. Just take the first line with data:
        for line in lines:
            # Ignore empty lines
            if not line.startswith('data: '):
                continue
            # When the last chunk is received, send the entire message
            if line.startswith('data: [DONE]'):
                content = ''.join(self.tokens)
                self.params['messages'].append({'role': 'assistant', 'content': content})
                self.write_message('')
                self.tokens = []
                continue
            data = json.loads(line[6:])
            # TODO: Handle multiple responses in data['choices'], i.e. n > 1, properly
            delta = data['choices'][0]['delta']
            # Not all deltas have content. Starting and ending deltas don't. Skip them
            if 'content' in delta:
                token = delta['content']
                self.tokens.append(token)
                self.write_message(token)
