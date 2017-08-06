import os
from . import server
from . import TestGramex
from testfixtures import LogCapture


class TestURLLog(TestGramex):
    def check_log(self, url, separator):
        r = self.get(url, params={'x': '1'}, headers={'head': 'abc'}, cookies={'sid': 'mysid'})
        parts = r.text.strip().split(separator)
        columns = ['time', 'method', 'uri', 'ip', 'status', 'duration', 'user', 'error', 'args.x',
                   'request.protocol', 'headers.head', 'cookies.sid', 'user.id', 'env.HOME']
        self.assertEqual(len(parts), len(columns))
        log = dict(zip(columns, parts))
        self.assertDictContainsSubset({
            'method': 'GET',
            'uri': url + '?x=1',
            'status': '200',
            'error': 'ZeroDivisionError: integer division or modulo by zero',
            'args.x': '1',
            # 'user': '',
            # 'user.id', '',
            'request.protocol': 'http',
            'headers.head': 'abc',
            'cookies.sid': 'mysid',
            'env.HOME': os.path.expanduser('~'),
        }, log)
        self.assertIn(log['ip'], ('127.0.0.1', '::1'))
        try:
            float(log['time'])
        except ValueError:
            self.fail('time is not a number')
        try:
            float(log['duration'])
        except ValueError:
            self.fail('duration is not a number')

    def test_log_format(self):
        self.check_log('/logtest', separator='|')

    def test_log_csv(self):
        self.check_log('/logcsv', separator=',')
