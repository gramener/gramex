import os
import unittest
from gramex.debug import timer, Timer
from testfixtures import LogCapture


class TestDebug(unittest.TestCase):
    def test_timer(self):
        with LogCapture() as logs:
            timer('start')
            timer('middle')
        args = [rec.args for rec in logs.records
                if len(rec.args) > 2 and 'test_debug.py:test_timer' in rec.args[2]]
        self.assertEqual(len(args), 2)
        self.assertEqual(
            [arg[1] for arg in args],
            ['start', 'middle'])
        self.assertEqual(
            [arg[2].split(os.sep)[-1].rsplit(':', 1)[0] for arg in args],
            ['test_debug.py:test_timer', 'test_debug.py:test_timer'])

        with LogCapture() as logs:
            with Timer('msg'):
                pass
        args = [rec.args for rec in logs.records
                if len(rec.args) > 2 and 'test_debug.py:test_timer' in rec.args[2]]
        self.assertEqual(len(args), 1)
        self.assertEqual(
            [arg[1] for arg in args],
            ['msg'])
        self.assertEqual(
            [arg[2].split(os.sep)[-1].rsplit(':', 1)[0] for arg in args],
            ['test_debug.py:test_timer'])
