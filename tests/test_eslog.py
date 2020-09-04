from nose.tools import eq_
from . import TestGramex


class TestESLog(TestGramex):
    def test_elog(self):
        self.check('/log', {'level': 'INFO', 'x': 1, 'msg': 'abc'})
        result = self.check('/log/queue').json()
        eq_(result['level'], 'INFO')
        eq_(result['x'], '1')
        eq_(result['msg'], 'abc')
        eq_(result['port'], '9999')
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
