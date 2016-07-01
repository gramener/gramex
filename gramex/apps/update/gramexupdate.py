import os
import json
import logging
import gramex
from gramex.handlers.basehandler import BaseHandler

BAD_REQUEST = 400


class GramexUpdateHandler(BaseHandler):
    @classmethod
    def setup(cls, **kwargs):
        super(GramexUpdateHandler, cls).setup(**kwargs)
        cls.log = logging.getLogger('gramexupdate')
        cls.json_kwargs = {'ensure_ascii': True, 'separators': (',', ':')}
        folder = os.path.dirname(os.path.abspath(__file__))
        cls.template = os.path.join(folder, 'index.html')

    def get(self):
        # When a user casually visits the page, render friendly output
        self.render(self.template, version=gramex.__version__)

    def post(self):
        # Log all messages
        try:
            logs = json.loads(self.request.body, encoding='utf-8')
            assert isinstance(logs, list)
        except (ValueError, AssertionError):
            self.set_status(BAD_REQUEST)
            self.finish('Invalid POST data. Expecting JSON array')
            return
        for log in logs:
            log['ip'] = self.request.remote_ip
            self.log.info(json.dumps(log, **self.json_kwargs))
        # Return the latest Gramex version
        self.write(json.dumps({
            'version': gramex.__version__
        }, **self.json_kwargs))

    def check_xsrf_cookie(self):
        # Anyone with Gramex can post to this app. Ignore the xsrf token
        pass
