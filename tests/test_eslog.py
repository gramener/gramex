import os
import json
import requests
from gramex.http import OK
from nose.tools import eq_
from nose.plugins.skip import SkipTest
from .server import base_url
from . import TestGramex


class TestESLog(TestGramex):
    @classmethod
    def setUpClass(cls):
        r = requests.get(base_url + '/gramexlog/delete')
        if r.status_code != OK:
            raise SkipTest('Unable to connect to elasticsearch')

    def test_default(self):
        self.check('/gramexlog/delete')
        # If no arguments are specified, logs an empty dict
        self.check('/gramexlog/default')
        # Logs any URL query parameters specified
        self.check('/gramexlog/default', {'x': [1, 2], '高': 'σ', 'س': ''})
        for attempt in range(10, -1, -1):
            result = self.check('/gramexlog/search?index=default').json()['hits']
            try:
                eq_(json.dumps(result, sort_keys=True), json.dumps([
                    {},
                    {'x': '2', '高': 'σ', 'س': ''},
                ], sort_keys=True))
            except Exception:
                if attempt == 0:
                    raise

    def test_extra(self, status=200, port=9999):
        self.check('/gramexlog/delete')
        self.check('/gramexlog/extra')
        self.check('/gramexlog/extra', {'x': [1, 2], '高': 'σ', 'س': ''})
        for attempt in range(10, -1, -1):
            rows = self.check('/gramexlog/search?index=extra').json()['hits']
            try:
                eq_(len(rows), 2)
                for row in rows:
                    eq_(row['int'], 1)
                    eq_(row['bool'], True)
                    eq_(row['str'], 'msg')
                    eq_(row['none'], None)
                    eq_(row['name'], 'gramexlog/extra')
                    eq_(row['class'], 'FunctionHandler')
                    eq_(row['method'], 'GET')
                    eq_(row['uri'], '/gramexlog/extra')
                    eq_(row['status'], status)
                    eq_(row['port'], port)
                    eq_(row['error'], '')
                    eq_(row['request.path'], '/gramexlog/extra')
                    eq_(row['headers.Host'], 'localhost:9999')
                    eq_(row['cookies.sid'], '')
                    eq_(row['user.id'], '')
                    eq_(row['env.HOME'], os.environ['HOME'])
                    eq_(row['args.y'], '')
                eq_(rows[0]['args.x'], '')
                eq_(rows[1]['args.x'], '2')
                eq_(rows[1]['x'], '2')
                eq_(rows[1]['高'], 'σ')
                eq_(rows[1]['س'], '')
            except Exception:
                if attempt == 0:
                    raise

    def test_nonexistent(self):
        # Even non-existent logging requests will succeed.
        # Gramex will wait for the (nonexistent) server to come up.
        self.check('/gramexlog/nonexistent')
        # TODO: check that the logs report errors when trying to connect

    @classmethod
    def tearDownClass(cls):
        requests.get(base_url + '/gramexlog/delete')
