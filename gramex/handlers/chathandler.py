from tornado.gen import coroutine
from gramex.handlers import BaseHandler


class ChatHandler(BaseHandler):
    @coroutine
    def get(self):
        self.write('Chat response')
