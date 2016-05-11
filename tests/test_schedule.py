from six.moves import http_client
from .test_handlers import TestGramex
from gramex.services import info


class TestSchedule(TestGramex):
    def test_schedule(self):
        self.assertIn('schedule-key', info, 'Schedule was run at startup')
        self.check('/', code=http_client.OK)
        self.assertTrue(0 < info['schedule-count'] < 200, 'Schedule still running')
