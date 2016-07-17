import os
from . import server
from . import TestGramex
from testfixtures import LogCapture


class TestURLLog(TestGramex):
    def test_log(self):
        r = r = self.get('/logtest?x=1', headers={'head': 'abc'})
        parts = r.text.split(' ')
        # Log format has 10 items. These are the first 5:
        # %(method)s %(uri)s %(ip)s %(status)s %(duration)s
        self.assertEqual(len(parts), 10)
        self.assertEqual(parts[0], 'GET')
        self.assertEqual(parts[1], '/logtest?x=1')
        self.assertIn(parts[2], ('127.0.0.1', '::1'))
        self.assertEqual(parts[3], '200')
        try:
            float(parts[4])
        except ValueError:
            self.fail('/logtest duration is not a number')

        # The next 5:
        # %(args.x)s %(headers.head)s %(cookies.sid)s %(user.id)s %(env.HOME)s
        self.assertEqual(parts[5], '1')
        self.assertEqual(parts[6], 'abc')
        # self.assertEqual(parts[7], sid)
        # self.assertEqual(parts[8], sid)
        self.assertEqual(parts[9], os.environ['HOME'])
