import os
import gramex
from . import server
from .test_handlers import TestGramex

setUpModule = server.start_gramex
tearDownModule = server.stop_gramex


class TestProcessHandler(TestGramex):
    folder = os.path.dirname(os.path.abspath(__file__))

    def check_result(self, url, code=200, cmd=None, cwd=None, stdout=True, stderr=True):
        cmd = cmd or self.folder + '/processtest.py'
        cwd = cwd or gramex.paths.base.absolute()
        r = self.get(url)
        self.assertEqual(r.status_code, code)
        lines = [line.strip() for line in r.text.split('\n')]
        if stdout:
            self.assertIn('stdout starts', lines)
            self.assertIn('stdout ends', lines)
            self.assertIn('os.getcwd: %s' % cwd, lines)
            self.assertIn('sys.argv[0]: %s' % cmd, lines)
            self.assertIn('sys.argv[1]: a', lines)
            self.assertIn('sys.argv[2]: 1', lines)
            self.assertIn('sys.argv[3]: x y', lines)
        else:
            self.assertNotIn('stdout starts', lines)
        if stderr:
            self.assertIn('stderr starts', lines)
            self.assertIn('stderr ends', lines)
        else:
            self.assertNotIn('stderr starts', r.text)

    def test_args(self):
        self.check_result('/process/args')

    def test_streams(self):
        self.check_result('/process/args-no-stdout', stdout=False)
        self.check_result('/process/args-no-stderr', stderr=False)

    def test_shell(self):
        self.check_result(url='/process/shell')

    def test_cwd(self):
        cwd = str(gramex.paths.base.absolute().parent)
        self.check_result(url='/process/cwd', cwd=cwd)
