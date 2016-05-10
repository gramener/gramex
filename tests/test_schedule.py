import io
import os
import six
import sys
import time
from pydoc import locate
from . import server
from .test_handlers import TestGramex
from gramex.services import info

setUpModule = server.start_gramex
tearDownModule = server.stop_gramex


class TestSchedule(TestGramex):
    def test_schedule(self):
        self.assertIn('schedule-key', info, 'Schedule was run at startup')
        self.check('/', code=200)
        self.assertTrue(0 < info['schedule-count'] < 200, 'Schedule still running')
