import os
import json
import time
import logging
import tornado.web
import tornado.escape
from .basehandler import BaseHandler

_datastore = {}         # Contents of the JSON data stores
_loaded = {}            # Time when persistent stores were last loaded


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
        except json.decoder.JSONDecodeError:
            raise tornado.web.HTTPError(400, log_message='Bad JSON', reason='Bad JSON')

    def jsonwalk(self, jsonpath, create=False):
        ''
        if self.path:
            pathkey = self.path
            _datastore.setdefault(pathkey, None)
            self.changed = False
            if os.path.exists(pathkey):
                # Initialise data from file if it's beeup updated
                if _loaded.get(pathkey, 0) <= os.stat(pathkey).st_mtime:
                    # Don't use encoding when reading JSON. We're using ensure_ascii=True
                    # Besides, when handling Py2 & Py3, just ignoring encoding works best
                    with open(pathkey, mode='r') as handle:     # noqa
                        try:
                            _datastore[pathkey] = json.load(handle)
                            _loaded[pathkey] = time.time()
                        except ValueError:
                            logging.warn('Invalid JSON in %s', pathkey)
                            self.changed = True
            else:
                self.changed = True
        else:
            pathkey = self.name
            _datastore.setdefault(pathkey, self.default_data)

        # Walk down the path and find the parent, key and data represented by jsonpath
        parent, key, data = _datastore, pathkey, _datastore[pathkey]
        if not jsonpath:
            return parent, key, data
        keys = [pathkey] + jsonpath.split('/')
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
        self.name = kwargs['name']
        self.path = path
        self.default_data = data
        self.json_kwargs = {
            'ensure_ascii': True,
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
        if self.request.body:
            data = parent[key] = self.parse_body_as_json()
            self.write(json.dumps(data, **self.json_kwargs))
            self.changed = True

    def patch(self, jsonpath):
        parent, key, data = self.jsonwalk(jsonpath)
        if data is not None:
            data = self.parse_body_as_json()
            parent[key].update(data)
            self.changed = True
        self.write(json.dumps(data, **self.json_kwargs))

    def delete(self, jsonpath):
        parent, key, data = self.jsonwalk(jsonpath)
        if data is not None:
            del parent[key]
            self.changed = True
        self.write('null')

    def on_finish(self):
        # Write data to disk if changed
        if self.path and self.changed:
            # Don't use encoding when reading JSON. We're using ensure_ascii=True
            # Besides, when handling Py2 & Py3, just ignoring encoding works best
            with open(self.path, mode='w') as handle:       # noqa
                json.dump(_datastore.get(self.path), handle, **self.json_kwargs)
            _loaded[self.path] = time.time()
