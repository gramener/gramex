from tornado.gen import coroutine
from gramex.handlers import BaseHandler

info = {}


@coroutine
def get_agent(config_dir):
    # If rasa is not installed, let it raise an ImportError
    from rasa.core.agent import Agent

    if 'agent' not in info:
        info['agent'] = Agent.load(model_path=config_dir)
        # TODO: Await till agent.is_ready()
    return info['agent']


class ChatHandler(BaseHandler):
    @classmethod
    def setup(cls, config_dir='.', **kwargs):
        super(ChatHandler, cls).setup(**kwargs)
        cls.config_dir = config_dir

    @coroutine
    def get(self):
        agent = yield get_agent(self.config_dir)
        message = self.get_arg('q')
        coroutine = agent.handle_text(message)
        responses = yield coroutine
        self.write(responses)
