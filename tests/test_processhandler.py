import os
import gramex
from . import server
from .test_handlers import TestGramex

setUpModule = server.start_gramex
tearDownModule = server.stop_gramex


class TestProcessHandler(TestGramex):
    folder = os.path.dirname(os.path.abspath(__file__))

    def check_result(self, url, cmd=None, cwd=None, stdout=True, stderr=True):
        cmd = cmd or self.folder + '/utils.py'
        cwd = cwd or gramex.paths.base.absolute()
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        if stdout:
            self.assertIn('stdout starts', r.text)
            self.assertIn('stdout ends', r.text)
            self.assertIn('sys.argv[0]: %s' % cmd, r.text)
            self.assertIn('sys.argv[1]: a', r.text)
            self.assertIn('sys.argv[2]: 1', r.text)
            self.assertIn('sys.argv[3]: x y', r.text)
        else:
            self.assertNotIn('stdout starts', r.text)
        if stderr:
            self.assertIn('stderr starts', r.text)
            self.assertIn('stderr ends', r.text)
        else:
            self.assertNotIn('stderr starts', r.text)

    def test_args(self):
        self.check_result('/process/args')

    def test_shell(self):
        self.check_result(url='/process/shell')

    def test_cwd(self):
        cwd = str(gramex.paths.base.absolute().parent)
        self.check_result(url='/process/shell', cwd=cwd)
