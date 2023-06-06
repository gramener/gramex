import json
from .basehandler import BaseWebSocketHandler
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient
from typing import Dict, Any


class ChatGPTHandler(BaseWebSocketHandler):
    '''A WebSocketHandler that proxies requests to OpenAI chat completions.

    Configuration:

    ```yaml
        handler: ChatGPTHandler
        kwargs:
          key: ...
          default:
            model: gpt-3.5-turbo
            temperature: 1
            ...
    ```
    '''

    @classmethod
    def setup(
        cls,
        key: str = '',
        url: str = 'https://api.openai.com/v1/chat/completions',
        default: Dict[str, Any] = None,
        **kwargs,
    ):
        super(BaseWebSocketHandler, cls).setup(**kwargs)

        cls.url = url
        cls.default = default or {}
        cls.headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
        cls.http = AsyncHTTPClient()

    def open(self):
        self.params = dict(self.default)
        self.params.setdefault('model', 'gpt-3.5-turbo')
        self.params.setdefault('messages', [])
        self.params.setdefault('stream', 'stream' in self.args)

    @coroutine
    def on_message(self, message: str):
        self.params['messages'].append({'role': 'user', 'content': message})
        kwargs = {}
        if self.params['stream']:
            kwargs['streaming_callback'] = self.on_chunk
            self.chunks, self.tokens = [], []
        try:
            r = yield self.http.fetch(
                'https://api.openai.com/v1/chat/completions',
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
        elif r.body:
            data = json.loads(r.body)
            # TODO: Handle multiple responses in data['choices'], i.e. n > 1, properly
            content = data['choices'][0]['message']['content']
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
