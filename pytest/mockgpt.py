import json
import gramex.cache
from gramex.handlers import BaseHandler, ChatGPTHandler
import time
from tornado.gen import coroutine, sleep


class ChatHandler(BaseHandler):
    def prepare(self):
        super().prepare()
        self.update_body_args()

    @coroutine
    def post(self):
        if 'Authorization' not in self.request.headers:
            return self.raise_error(401, 'no-api-key')
        if not self.request.headers.get('Authorization', '').startswith('Bearer TEST-KEY'):
            return self.raise_error(401, 'wrong-api-key')
        if 'messages' not in self.args:
            return self.raise_error(400, 'no-messages')
        content = '\n'.join(
            [msg['content'] for msg in self.args['messages'] if msg['role'] == 'user']
        )
        for arg in self.args:
            if arg not in set(ChatGPTHandler._params_defaults.keys()) | {'messages'}:
                return self.raise_error(400, 'invalid-argument')
        if self.args.get('stream', False):
            for char in content:
                yield sleep(0.1)
                frame = {"choices": [{"delta": {"content": char}}]}
                self.write(f'data: {json.dumps(frame)}\n\n')
                self.flush()
            self.write('data: [DONE]\n\n')
            self.flush()
        else:
            self.write(self.message(content))

    def raise_error(self, code, error):
        config = gramex.cache.open('mockgpt.yaml', rel=True)
        errors = config['errors']
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({"error": errors[error]}))
        self.set_status(code)

    def message(self, content):
        return {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": time.time(),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 9, "completion_tokens": 12, "total_tokens": 21},
        }
