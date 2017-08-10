import io
import os
import time
import gramex
from . import TestGramex


class TestProcessHandler(TestGramex):
    folder = os.path.dirname(os.path.abspath(__file__))

    def check_stdout(self, lines, stdout, cwd=None):
        '''Check if the lines emitted contain the right stdout values'''
        if stdout:
            cmd = self.folder + '/processtest.py'
            cwd = cwd or gramex.paths.base.absolute()
            self.assertIn('stdout starts', lines)
            self.assertIn('stdout ends', lines)
            self.assertIn('os.getcwd: %s' % cwd, lines)
            self.assertIn('sys.argv[0]: %s' % cmd, lines)
            self.assertIn('sys.argv[1]: a', lines)
            self.assertIn('sys.argv[2]: 1', lines)
            self.assertIn('sys.argv[3]: x y', lines)
        else:
            self.assertNotIn('stdout starts', lines)

    def check_stderr(self, lines, stderr):
        '''Check if the lines emitted contain the right stderr values'''
        if stderr:
            self.assertIn('stderr starts', lines)
            self.assertIn('stderr ends', lines)
        else:
            self.assertNotIn('stderr starts', lines)

    def check_path(self, path, cwd=None, stdout=True, stderr=True):
        '''Check if the path has the right stdout/stderr values'''
        path = os.path.join(self.folder, path)
        self.assertTrue(os.path.exists(path))
        # Wait a bit until the path is closed, then open it and return the handle
        delay = 0.1
        time.sleep(delay)
        handle = io.open(path, encoding='utf-8')
        try:
            lines = [line.strip() for line in handle.readlines()]
            self.check_stdout(lines, stdout, cwd=cwd)
            self.check_stderr(lines, stderr)
        finally:
            handle.close()
            os.unlink(path)

    def check_url(self, url, code=200, cwd=None, stdout=True, stderr=True):
        r = self.get(url)
        self.assertEqual(r.status_code, code)
        lines = [line.strip() for line in r.text.split('\n')]
        self.check_stdout(lines, stdout, cwd=cwd)
        self.check_stderr(lines, stderr)

    def test_args(self):
        self.check_url('/process/args')

    def test_streams(self):
        self.check_url('/process/args-pipe')
        self.check_url('/process/args-no-stdout', stdout=False)
        self.check_url('/process/args-no-stderr', stderr=False)

        self.check_url('/process/args-stdout-file', stdout=False)
        self.check_path('processtest.stdout', stderr=False)

        self.check_url('/process/args-both-file', stdout=False, stderr=False)
        self.check_path('processtest.both')

    def test_multistream(self):
        self.check_url('/process/args-multi-file')
        self.check_path('processtest.stdout.1', stderr=False)
        self.check_path('processtest.stderr.1', stdout=False)
        self.check_path('processtest.stdout.2', stderr=False)
        self.check_path('processtest.stderr.2', stdout=False)

    def test_shell(self):
        self.check_url(url='/process/shell')

    def test_cwd(self):
        cwd = str(gramex.paths.base.absolute().parent)
        self.check_url(url='/process/cwd', cwd=cwd)

    def test_errors(self):
        self.check(url='/process/nonexistent-command', code=500)
        self.check(url='/process/error', code=200, text='ZeroDivisionError')
