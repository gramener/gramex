import os
import unittest
from gramex.debug import timer, Timer
from testfixtures import LogCapture


class TestDebug(unittest.TestCase):
    def test_timer(self):
        with LogCapture() as logs:
            timer('start')
            timer('middle')
        self.assertGreaterEqual(len(logs.records), 2)
        self.assertGreaterEqual(
            {rec.args[1] for rec in logs.records},
            {'start', 'middle'})
        self.assertGreaterEqual(
            {rec.args[2].split(os.sep)[-1].rsplit(':', 1)[0] for rec in logs.records},
            {'test_debug.py:test_timer', 'test_debug.py:test_timer'})

        with LogCapture() as logs:
            with Timer('msg'):
                pass
        self.assertGreaterEqual(len(logs.records), 1)
        self.assertGreaterEqual(
            {rec.args[1] for rec in logs.records},
            {'msg'})
        self.assertGreaterEqual(
            {rec.args[2].split(os.sep)[-1].rsplit(':', 1)[0] for rec in logs.records},
            {'test_debug.py:test_timer'})
