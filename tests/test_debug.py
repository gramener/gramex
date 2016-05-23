import unittest
from gramex.debug import timer, Timer
from testfixtures import LogCapture


class TestDebug(unittest.TestCase):
    def test_timer(self):
        with LogCapture() as logs:
            timer('start')
            timer('middle')
        self.assertEqual(len(logs.records), 2)
        self.assertEqual('start', logs.records[0].args[1])
        self.assertEqual('middle', logs.records[1].args[1])
        self.assertIn('test_debug.py:test_timer', logs.records[0].args[2])
        self.assertIn('test_debug.py:test_timer', logs.records[1].args[2])

        with LogCapture() as logs:
            with Timer('msg'):
                pass
        self.assertEqual(len(logs.records), 1)
        self.assertEqual('msg', logs.records[0].args[1])
        self.assertIn('test_debug.py:test_timer', logs.records[0].args[2])
