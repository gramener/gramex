import os
from tornado.gen import coroutine
from gramex.cache import daemon
from gramex.handlers import BaseHandler

info = {}


@coroutine
def get_agent(config_dir):
    # If rasa is not installed, let it raise an ImportError
    from rasa.core.agent import Agent, EndpointConfig
    from rasa.core.tracker_store import SQLTrackerStore

    if 'tracker' not in info:
        info['tracker'] = SQLTrackerStore(
            db=f'{config_dir}/tracker.db', dialect='sqlite')
    # TODO: Also reload model and restart actions server if it's out-of-date
    if 'agent' not in info:
        info['agent'] = Agent.load(
            model_path=config_dir,
            tracker_store=info['tracker'],
            action_endpoint=EndpointConfig('http://localhost:5055/webhook'))
        # TODO: Await till agent.is_ready()
        # TODO: Don't hard code actions path to test1.actions
        info['actionserver'] = yield daemon(
            ['rasa', 'run', 'actions', '--action', 'test1.actions'],
        )
    return info['agent']


class ChatHandler(BaseHandler):
    @classmethod
    def setup(cls, config_dir='.', **kwargs):
        super(ChatHandler, cls).setup(**kwargs)
        cls.config_dir = os.path.abspath(config_dir)

    @coroutine
    def get(self):
        agent = yield get_agent(self.config_dir)
        message = self.get_arg('q')
        coroutine = agent.handle_text(message, sender_id=self.session['id'])
        responses = yield coroutine
        self.write({"responses": responses})
