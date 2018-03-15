# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import json
import requests
import gramex
from contextlib import contextmanager
from . import server, TestGramex
from nose.tools import assert_raises, eq_


@contextmanager
def json_changes(path):
    size = os.stat(path).st_size if os.path.exists(path) else 0
    result = []
    yield result
    handle = open(path, 'rb')
    handle.seek(size)
    result += [json.loads(line) for line in handle.readlines()]


class TestUpdate(TestGramex):
    def test_update_app(self):
        # /update/ contains the current gramex version
        self.check('/update/', text=gramex.__version__)

        # post to /update/ with JSON list of keys. Updates url.gramexupdate.kwargs.path
        data = [{'x': 0, 'y': 1}, {'x': 2, 'y': 3}]
        with json_changes(gramex.conf.log.handlers['gramex-update-log'].filename) as changes:
            r = self.get('/update/', method='post', data=json.dumps(data))
        for output, source in zip(changes, data):
            self.assertDictContainsSubset(source, output)

        # The response contains the current version
        eq_(r.json(), {'version': gramex.__version__})

    def test_update_method(self):
        conn = gramex.services.info.eventlog.conn
        # Truncate the events database to ensure that the update check is ALWAYS performed
        conn.execute('DELETE FROM events')
        with assert_raises(requests.HTTPError):
            gramex.gramex_update(server.base_url + '/nonexistent/')

        # Only push latest events since last update
        conn.execute('DELETE FROM events')
        conn.execute('INSERT INTO events VALUES (?, ?, ?)', [0, 'startup', ''])
        conn.execute('INSERT INTO events VALUES (?, ?, ?)', [1, 'shutdown', ''])
        conn.execute('INSERT INTO events VALUES (?, ?, ?)', [2, 'update', ''])
        conn.execute('INSERT INTO events VALUES (?, ?, ?)', [3, 'startup', ''])
        conn.execute('INSERT INTO events VALUES (?, ?, ?)', [4, 'shutdown', ''])
        conn.commit()
        result = gramex.gramex_update(server.base_url + '/update/')
        # Only the last 2 events are sent
        eq_(len(result['logs']), 2)
        eq_(result['logs'][0]['time'], 3)
        eq_(result['logs'][1]['time'], 4)
        eq_(result['response']['version'], gramex.__version__)

        # Once updated, don't run the update again
        result = gramex.gramex_update(server.base_url + '/update/')
        eq_(result, None)
