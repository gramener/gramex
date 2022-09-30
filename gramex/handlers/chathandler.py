import os
from tornado.gen import coroutine
from gramex.cache import daemon
from gramex.handlers import BaseHandler

info = {}


@coroutine
def get_agent(config_dir, action_port=None):
    # If rasa is not installed, let it raise an ImportError
    from rasa.core.agent import Agent, EndpointConfig
    from rasa.core.tracker_store import SQLTrackerStore

    if 'tracker' not in info:
        info['tracker'] = SQLTrackerStore(
            db=f'{config_dir}/tracker.db', dialect='sqlite')
    # TODO: 3. Also reload model and restart actions server if it's out-of-date
    if 'agent' not in info:
        kwargs = {}
        if action_port:
            # NOTE: Later, allow multiple Gramex instances to use a single existing rasa bot
            info['actionserver'] = yield daemon([
                'rasa', 'run', 'actions', '--action', 'actions', '--port', f'{action_port}'
            ], cwd=config_dir)
            # TODO: Check rasa binds to IPv6, and we don't need to use ::1 instead of 127.0.0.1
            kwargs['action_endpoint'] = EndpointConfig(f'http://127.0.0.1:{action_port}/webhook')
        info['agent'] = Agent.load(
            model_path=config_dir,
            tracker_store=info['tracker'], **kwargs)
        # TODO: 2. Await till agent.is_ready()
    return info['agent']


class ChatHandler(BaseHandler):
    @classmethod
    def setup(cls, config_dir='.', action_port=None, **kwargs):
        super(ChatHandler, cls).setup(**kwargs)
        cls.config_dir = os.path.abspath(config_dir)
        cls.action_port = action_port

    @coroutine
    def get(self):
        agent = yield get_agent(self.config_dir, self.action_port)
        message = self.get_arg('q')
        coroutine = agent.handle_text(message, sender_id=self.session['id'])
        responses = yield coroutine
        self.write({"responses": responses})
