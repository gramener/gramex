import os
import json
import time
import logging
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
    :arg string data: optional initial dataset, if path does not exist. Defaults
        to null
    '''
    def jsonwalk(self, jsonpath, create=False):
        ''
        # Path key defaults to the URL spec name.
        # Set the default data provided.
        pathkey = self.name if self.path is None else self.path
        _datastore.setdefault(pathkey, self.default_data)

        if self.path:
            self.changed = False
            if os.path.exists(pathkey):
                # Initialise data from file
                if _loaded.get(pathkey, 0) <= os.stat(pathkey).st_mtime:
                    with open(pathkey, mode='rb') as handle:
                        try:
                            _datastore[pathkey] = json.load(handle, encoding='utf-8')
                            _loaded[pathkey] = time.time()
                        except ValueError:
                            logging.warn('Invalid JSON in %s', pathkey)
                            self.changed = True
            elif _datastore[pathkey] is not None:
                self.changed = True

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
        self.changed = True

    def patch(self, jsonpath):
        parent, key, data = self.jsonwalk(jsonpath)
        if data is not None:
            data = tornado.escape.json_decode(self.request.body)
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
            with open(self.path, mode='wb') as handle:
                json.dump(_datastore.get(self.path), handle, encoding='utf-8', **self.json_kwargs)
            _loaded[self.path] = time.time()
