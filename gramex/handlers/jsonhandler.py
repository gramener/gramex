import os
import json
import time
import uuid
import tornado.web
import tornado.escape
from .basehandler import BaseHandler
from gramex.config import app_log

# JSONHandler data is stored in store. Each handler is specified with a path.
# store[path] holds the full data for that handler. It is saved in path at the
# end of each request (if the data has changed.) The time data was last synced is
# stored in _loaded[path].
store = {}              # Contents of the JSON data stores
_loaded = {}            # Time when persistent stores were last loaded
_jsonstores = store     # Internal legacy alias for store


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
    :arg string data: optional initial dataset, used only if path is not
        specified. Defaults to null
    '''
    def parse_body_as_json(self):
        try:
            return tornado.escape.json_decode(self.request.body)
        except ValueError:
            raise tornado.web.HTTPError(status_code=400, log_message='Bad JSON', reason='Bad JSON')

    def jsonwalk(self, jsonpath, create=False):
        '''Return a parent, key, value from the JSON store where parent[key] == value'''
        # Load data from self.path JSON file if it's specified, exists, and newer than last load.
        # Otherwise, load the default data provided.
        if self.path:
            path = self.path
            _jsonstores.setdefault(path, None)
            self.changed = False
            if os.path.exists(path):
                if _loaded.get(path, 0) <= os.stat(path).st_mtime:
                    # Don't use encoding when reading JSON. We're using ensure_ascii=True
                    # Besides, when handling Py2 & Py3, just ignoring encoding works best
                    with open(path, mode='r') as handle:     # noqa
                        try:
                            _jsonstores[path] = json.load(handle)
                            _loaded[path] = time.time()
                        except ValueError:
                            app_log.warning('Invalid JSON in %s', path)
                            self.changed = True
            else:
                self.changed = True
        else:
            path = self.name
            _jsonstores.setdefault(path, self.default_data)

        # Walk down the path and find the parent, key and data represented by jsonpath
        parent, key, data = _jsonstores, path, _jsonstores[path]
        if not jsonpath:
            return parent, key, data
        keys = [path] + jsonpath.split('/')
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

    @classmethod
    def setup(cls, path=None, data=None, **kwargs):
        super(JSONHandler, cls).setup(**kwargs)
        cls.path = path
        cls.default_data = data
        cls.json_kwargs = {
            'ensure_ascii': True,
            'separators': (',', ':'),
        }

    def initialize(self, **kwargs):
        super(JSONHandler, self).initialize(**kwargs)
        self.set_header('Content-Type', 'application/json')

    def get(self, jsonpath):
        '''Return the JSON data at jsonpath. Return null for invalid paths.'''
        parent, key, data = self.jsonwalk(jsonpath, create=False)
        self.write(json.dumps(data, **self.json_kwargs))

    def post(self, jsonpath):
        '''Add data as a new unique key under jsonpath. Return {name: new_key}'''
        parent, key, data = self.jsonwalk(jsonpath, create=True)
        if self.request.body:
            if data is None:
                parent[key] = data = {}
            new_key = str(uuid.uuid4())
            data[new_key] = self.parse_body_as_json()
            self.write(json.dumps({'name': new_key}, **self.json_kwargs))
            self.changed = True
        else:
            self.write(json.dumps(None))

    def put(self, jsonpath):
        '''Set JSON data at jsonpath. Return the data provided'''
        parent, key, data = self.jsonwalk(jsonpath, create=True)
        if self.request.body:
            data = parent[key] = self.parse_body_as_json()
            self.write(json.dumps(data, **self.json_kwargs))
            self.changed = True
        else:
            self.write(json.dumps(None))

    def patch(self, jsonpath):
        '''Update JSON data at jsonpath. Return the data provided'''
        parent, key, data = self.jsonwalk(jsonpath)
        if data is not None:
            data = self.parse_body_as_json()
            parent[key].update(data)
            self.changed = True
        self.write(json.dumps(data, **self.json_kwargs))

    def delete(self, jsonpath):
        '''Delete data at jsonpath. Return null'''
        parent, key, data = self.jsonwalk(jsonpath)
        if data is not None:
            del parent[key]
            self.changed = True
        self.write('null')

    def on_finish(self):
        # Write data to disk if changed. on_finish is called after writing the
        # data, so the client is not waiting for the response.
        if self.path and getattr(self, 'changed', False):
            folder = os.path.dirname(os.path.abspath(self.path))
            if not os.path.exists(folder):
                os.makedirs(folder)
            # Don't use encoding when reading JSON. We use ensure_ascii=True.
            # When handling Py2 & Py3, just ignoring encoding works best.
            with open(self.path, mode='w') as handle:       # noqa
                json.dump(_jsonstores.get(self.path), handle, **self.json_kwargs)
            _loaded[self.path] = time.time()
        super(JSONHandler, self).on_finish()
