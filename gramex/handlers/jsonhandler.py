import json
import tornado.escape
from .basehandler import BaseHandler

# TODO: populate this via services.url hook and from path data
datastore = {}


class JSONHandler(BaseHandler):
    '''
    Provides a REST API for managing and persisting JSON data.

    Sample URL configuration::

        pattern: /$YAMLURL/data/(.*)
        handler: JSONHandler
        kwargs:
            path: $YAMLPATH/data.json

    :arg string path: optional file where the JSON data is persisted. If not
        specified, the JSON data is not persisted.
    :arg string data: optional initial dataset. Defaults to null
    '''
    def jsonwalk(self, jsonpath, create=False):
        ''
        # Path key defaults to the portion of the URL before the jsonpath
        if self.path is None:
            full_path = tornado.escape.url_unescape(self.request.path)
            self.path = full_path[:len(full_path) - len(jsonpath)]

        # Set the default data provided.
        # TODO: make this a one-type setup via services.url hooks
        datastore.setdefault(self.path, self.default_data)

        # TODO: data persistence

        parent, key, data = datastore, self.path, datastore[self.path]
        if not jsonpath:
            return parent, key, data
        keys = [self.path] + jsonpath.split('/')
        for index, key in enumerate(keys[1:]):
            if hasattr(data, '__contains__') and key in data:
                parent, data = data, data[key]
                continue
            if isinstance(data, list) and key.isdigit():
                key = int(key)
                if key < len(data):
                    parent, data = data, data[key]
                    continue
            if create:
                if not hasattr(data, '__contains__'):
                    parent[keys[index]] = data = {}
                data[key] = {}
                parent, data = data, data[key]
                continue
            return parent, key, None
        return parent, key, data

    def initialize(self, path=None, data=None, **kwargs):
        self.path = path
        self.default_data = data
        self.json_kwargs = {
            'separators': (',', ':'),
        }

        # Set the method to the ?x-http-method-overrride argument or the
        # X-HTTP-Method-Override header if they exist
        if 'x-http-method-override' in self.request.arguments:
            self.request.method = self.get_argument('x-http-method-override')
        elif 'X-HTTP-Method-Override' in self.request.headers:
            self.request.method = self.request.headers['X-HTTP-Method-Override']

        super(JSONHandler, self).initialize(**kwargs)
        self.set_header('Content-Type', 'application/json')

    def get(self, jsonpath):
        'Return the JSON data at jsonpath. HTTP Return null for invalid paths.'
        parent, key, data = self.jsonwalk(jsonpath, create=False)
        self.write(json.dumps(data, **self.json_kwargs))

    def post(self, jsonpath):
        # TODO: implement POST
        pass

    def put(self, jsonpath):
        parent, key, data = self.jsonwalk(jsonpath, create=True)
        data = parent[key] = tornado.escape.json_decode(self.request.body)
        self.write(json.dumps(data, **self.json_kwargs))

    def patch(self, jsonpath):
        parent, key, data = self.jsonwalk(jsonpath)
        if data is not None:
            data = tornado.escape.json_decode(self.request.body)
            parent[key].update(data)
        self.write(json.dumps(data, **self.json_kwargs))

    def delete(self, jsonpath):
        parent, key, data = self.jsonwalk(jsonpath)
        if data is not None:
            del parent[key]
        self.write('null')
