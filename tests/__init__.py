import requests
import unittest
from six.moves import http_client
from . import server
from gramex import conf
from gramex.services import info


def setUp():
    server.start_gramex()


def tearDown():
    server.stop_gramex()


class TestGramex(unittest.TestCase):
    'Base class to test Gramex running as a subprocess'

    def get(self, url, **kwargs):
        return requests.get(server.base_url + url, timeout=10, **kwargs)

    def check(self, url, path=None, code=200, text=None, no_text=None, headers=None):
        r = self.get(url)
        self.assertEqual(r.status_code, code, '%s: code %d != %d' % (url, r.status_code, code))
        if text is not None:
            self.assertIn(text, r.text, '%s: %s not in %s' % (url, text, r.text))
        if no_text is not None:
            self.assertNotIn(text, r.text, '%s: %s should not be in %s' % (url, text, r.text))
        if path is not None:
            with (server.info.folder / path).open('rb') as file:
                self.assertEqual(r.content, file.read(), '%s != %s' % (url, path))
        if headers is not None:
            for header, value in headers.items():
                if value is None:
                    self.assertFalse(header in r.headers,
                                     '%s: should not have header %s' % (url, header))
                else:
                    actual = r.headers[header]
                    self.assertEqual(actual, value,
                                     '%s: header %s = %s != %s' % (url, header, actual, value))
        return r


class TestSchedule(TestGramex):

    def test_schedule(self):
        # Run this test as soon as Gramex starts to check if schedule has run
        self.assertIn('schedule-key', info, 'Schedule was run at startup')
        self.check('/', code=http_client.OK)
        max_count = conf.schedule['schedule-startup-slow'].args[1] - 1
        self.assertTrue(0 < info['schedule-count'] < max_count, 'Schedule still running')
