import json
from .basehandler import BaseWebSocketHandler
from gramex.transforms import build_transform
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient
from typing import Callable, Union


class ChatGPTHandler(BaseWebSocketHandler):
    '''A WebSocketHandler that proxies requests to OpenAI chat completions.

    Configuration:

    ```yaml
        handler: ChatGPTHandler
        kwargs:
          key: ...
          max_history: ...
          default:
            model: gpt-3.5-turbo
            temperature: 1
            ...
    ```
    '''

    function_vars = {
        'open': {'params': None, 'handler': None},
        'prepare': {'msg': None, 'handler': None},
        'modify': {'msg': None, 'handler': None},
    }
    api_params = {
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
    def setup(
        cls,
        key: str = '',
        url: str = 'https://api.openai.com/v1/chat/completions',
        max_history: int = None,
        # See https://platform.openai.com/docs/models/model-endpoint-compatibility
        open: Union[Callable, str] = None,
        prepare: Union[Callable, str] = None,
        modify: Union[Callable, str] = None,
        **kwargs,
    ):
        super(BaseWebSocketHandler, cls).setup(**kwargs)

        cls.url = url
        cls.headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
        cls.max_history = max_history
        cls.info = {'open': open, 'prepare': prepare, 'modify': modify}
        cls.default = {}
        for k, v in cls.api_params.items():
            v = kwargs.pop(k, v)
            if isinstance(v, dict) and 'function' in v:
                cls.default[k] = build_transform(
                    v, filename=f'url:{cls.name}.{k}', vars={'handler': None}, iter=False
                )
            elif v is not None:
                cls.default[k] = v
        for k, v in cls.info.items():
            if v:
                cls.info[k] = build_transform(
                    {'function': v},
                    filename=f'url:{cls.name}.{k}',
                    vars=cls.function_vars[k],
                    iter=False,
                )

    def open(self):
        self.http = AsyncHTTPClient()
        self.params = {k: v(self) if callable(v) else v for k, v in self.default.items()}
        self.params.setdefault('messages', [])
        if callable(self.info['open']):
            self.info['open'](self.params, self)

    @coroutine
    def on_message(self, message: str):
        # Call prepare before updating the database
        if callable(self.info['prepare']):
            self.info['prepare'](msg=message, handler=self)

        if self.max_history is not None:
            self.params['messages'] = self.params['messages'][-self.max_history * 2 :]
        self.params['messages'].append({'role': 'user', 'content': message})
        kwargs = {}
        if self.params['stream']:
            kwargs['streaming_callback'] = self.on_chunk
            self.chunks, self.tokens = [], []
        try:
            r = yield self.http.fetch(
                self.url,
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
            if callable(self.info['modify']):
                result = self.info['modify'](msg=data, handler=self)
                if result is not None:
                    content = result
            self.params['messages'].append({'role': 'assistant', 'content': content})
            self.write_message(content)
            self.write_message('')

    def on_chunk(self, chunk: bytes):
        self.chunks.append(chunk)
        # Each chunk has a data: ... but the last chunk has an additional line with
        # data: [DONE]. We ignore that. Just take the first line with data:
        for text in chunk.decode('utf-8').strip().split('\n'):
            # Ignore empty lines
            if not text.startswith('data: '):
                continue
            # When the last chunk is received, send the entire message
            if text.startswith('data: [DONE]'):
                content = ''.join(self.tokens)
                self.params['messages'].append({'role': 'assistant', 'content': content})
                self.write_message('')
                continue
            data = json.loads(text[6:])
            # TODO: Handle multiple responses in data['choices'], i.e. n > 1, properly
            delta = data['choices'][0]['delta']
            # Not all deltas have content. Starting and ending deltas don't. Skip them
            if 'content' in delta:
                token = delta['content']
                self.tokens.append(token)
                self.write_message(token)
