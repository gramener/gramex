import os
import json
from tornado.gen import coroutine
from tornado.web import HTTPError
from gramex.pynode import Node
from gramex.handlers import BaseHandler
from gramex.config import variables
from gramex.http import BAD_REQUEST, INTERNAL_SERVER_ERROR

_info = {}
default_character = {"name":"aryan","emotion":"angry","pose":"handsinpocket"}

class ComicHandler(BaseHandler):
    @coroutine
    def get(self):
        if 'node' not in _info:
            _info['node'] = Node(port=9967, cwd=os.path.join(variables['GRAMEXAPPS'], 'ui'))
        node = _info['node']
        # Take the last argument, i.e. ?name=dee&name=ava => {name: ava}

        if len(self.args.keys()) != 0:
            args = {key: vals[-1] for key, vals in self.args.items()}
        else:
            args = default_character
        # Fetch the results via Comicgen
        result = yield node.js(code='return require("comicgen")(require("fs"))(args)', args=args)
        # If there's no error, set the header and send the result
        if result['error'] is None:
            headers = self.kwargs.get('headers', {})
            headers.setdefault('Content-Type', 'image/svg+xml')
            for key, val in headers.items():
                self.set_header(key, val)
            self.write(result['result'])
        elif isinstance(result, dict) and 'message' in result['error']:
            raise HTTPError(BAD_REQUEST, reason=result['error']['message'])
        else:
            raise HTTPError(INTERNAL_SERVER_ERROR, reason=json.dumps(result))
