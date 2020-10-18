from nose.tools import eq_
from . import TestGramex
import json
import time


class TestESLog(TestGramex):
    def test_eslog(self):
        self.check('/log', {'level': 'INFO', 'x': 1, 'msg': 'abc'})
        result = self.check('/log/queue')
        result = json.loads(result.content)
        eq_(result[0]['level'], 'INFO')
        eq_(result[0]['x'], '1')
        eq_(result[0]['msg'], 'abc')
        eq_(result[0]['port'], 9999)
        # TODO: Check that this is within 5 seconds of now
        # eq_(result['time'], )

        # This logs ``{level: INFO, x: 1, msg: abc, port: 9988, time: 2020-07-21 13:41:00}``.
        # 3 keys are added:

        # 1. ``level``: logging level. Defaults to INFO
        # 2. ``time``: current time as YYYY-MM-DD HH:MM:ZZ in UTC
        # 3. ``port``: application's current port

        # If a logging service like ElasticSearch has been configured, it will periodically flush
        # the logs into ElasticSearch.

        # Run without configuring gramexlog
        # Run after configuring gramexlog manually

        # Without eslog config, log queue should be empty
        # Check if the log is written to elastic search

    def test_eslog_not_running(self):
        # 1. Create a connection to a nonexistent elasticsearch port and send the request
        # 2. Stop elasticsearch and send a log message
        # self.check('/log', {'level': 'WARN', 'x': x, 'msg': 'abc'})
        pass

    def search_log_doc(self):
        import uuid
        x = uuid.uuid4()
        no_of_docs = 5
        for i in range(no_of_docs):
            self.check('/log', {'level': 'WARN', 'x': x, 'msg': i})
        time.sleep(5)
        result = self.check('/log/search', {'x': x})
        result = result.json()
        eq_(result['hits']['total']['value'], no_of_docs)

    def log_multiple_apps(self):
        def create_check_logs(app_name):
            import uuid
            x = uuid.uuid4()
            no_of_docs = 5
            for i in range(no_of_docs):
                self.check('/log', {'level': 'WARN', 'x': x, 'msg': i, '_app': app_name})
            time.sleep(10)
            result = self.check('/log/search', {'x': x, '_app': app_name})
            result = result.json()
            eq_(result['hits']['total']['value'], no_of_docs)

        create_check_logs(app_name='default')
        create_check_logs(app_name='test_app')
