import gramex.cache
import os
import re
import time
import unittest
from nose.tools import eq_, ok_, assert_raises
from . import folder

small_delay = 0.01


def wait(future):
    wait_till(future.done)
    return future.result()


def wait_till(condition):
    while not condition():
        time.sleep(small_delay)


class TestSubprocess(unittest.TestCase):
    args = ['python', os.path.join(folder, 'subprocess_check.py')]          # Instant result
    args1 = ['python', os.path.join(folder, 'subprocess_check.py'), '1']    # Result after delay
    hello = ['python', '-c', 'print("hello")']

    @staticmethod
    def msg(s):
        '''Returns the string + newline as UTF-8 bytestring'''
        return (s + os.linesep).encode('utf-8')

    def test_stream_none(self):
        proc = gramex.cache.Subprocess(self.args)
        stdout, stderr = [wait(future) for future in proc.wait_for_exit()]
        eq_(stdout, self.msg('OUT:0'))
        eq_(stderr, self.msg('ERR:0'))

        proc = gramex.cache.Subprocess(self.args1)
        stdout, stderr = [wait(future) for future in proc.wait_for_exit()]
        eq_(stdout, self.msg('OUT:0') + self.msg('OUT:1'))
        eq_(stderr, self.msg('ERR:0') + self.msg('ERR:1'))

    def test_stream_list(self):
        proc = gramex.cache.Subprocess(
            self.args, stream_stdout='list_out', stream_stderr='list_err', buffer_size='line')
        [wait(future) for future in proc.wait_for_exit()]
        eq_(proc.list_out, [self.msg('OUT:0')])
        eq_(proc.list_err, [self.msg('ERR:0')])

        proc = gramex.cache.Subprocess(
            self.args1, stream_stdout='list_out', stream_stderr='list_err', buffer_size='line')
        wait_till(lambda: len(proc.list_out) > 0)
        wait_till(lambda: len(proc.list_err) > 0)
        eq_(proc.list_out, [self.msg('OUT:0')])
        eq_(proc.list_err, [self.msg('ERR:0')])
        wait_till(lambda: len(proc.list_out) > 1)
        wait_till(lambda: len(proc.list_err) > 1)
        eq_(proc.list_out, [self.msg('OUT:0'), self.msg('OUT:1')])
        eq_(proc.list_err, [self.msg('ERR:0'), self.msg('ERR:1')])
        [wait(future) for future in proc.wait_for_exit()]
        eq_(proc.list_out, [self.msg('OUT:0'), self.msg('OUT:1')])
        eq_(proc.list_err, [self.msg('ERR:0'), self.msg('ERR:1')])

    def test_stream_queue(self):
        proc = gramex.cache.Subprocess(
            self.args, stream_stdout='queue_out', stream_stderr='queue_err')
        [wait(future) for future in proc.wait_for_exit()]
        eq_(proc.queue_out.get(), self.msg('OUT:0'))
        eq_(proc.queue_err.get(), self.msg('ERR:0'))

        proc = gramex.cache.Subprocess(
            self.args1, stream_stdout='queue_out', stream_stderr='queue_err', buffer_size='line')
        eq_(proc.queue_out.get(), self.msg('OUT:0'))
        eq_(proc.queue_err.get(), self.msg('ERR:0'))
        eq_(proc.queue_out.get(), self.msg('OUT:1'))
        eq_(proc.queue_err.get(), self.msg('ERR:1'))
        [wait(future) for future in proc.wait_for_exit()]
        eq_(proc.queue_out.qsize(), 0)
        eq_(proc.queue_err.qsize(), 0)

    def test_stream_blend(self):
        proc = gramex.cache.Subprocess(
            self.args1, stream_stdout='list_out', stream_stderr='list_out', buffer_size='line')
        [wait(future) for future in proc.wait_for_exit()]
        eq_(set(proc.list_out), {self.msg(s) for s in ('OUT:0', 'OUT:1', 'ERR:0', 'ERR:1')})

        proc = gramex.cache.Subprocess(
            self.args1, stream_stdout='queue_out', stream_stderr='queue_out', buffer_size='line')
        [wait(future) for future in proc.wait_for_exit()]
        items = set()
        for index in range(proc.queue_out.qsize()):
            items.add(proc.queue_out.get_nowait())
        eq_(items, {self.msg(s) for s in ('OUT:0', 'OUT:1', 'ERR:0', 'ERR:1')})

    def test_daemon_reuse(self):
        procs = [
            wait(gramex.cache.daemon(self.args)),
            wait(gramex.cache.daemon(self.args)),
            wait(gramex.cache.daemon(self.args1)),
        ]
        eq_(procs[0].proc.pid, procs[1].proc.pid)
        ok_(procs[0].proc.pid != procs[2].proc.pid)
        for proc in procs:
            [wait(future) for future in proc.wait_for_exit()]

    def test_daemon_stream(self):
        out = []
        proc = wait(gramex.cache.daemon(self.args, stream=out.append))
        [wait(future) for future in proc.wait_for_exit()]
        eq_(set(out), {self.msg('OUT:0'), self.msg('ERR:0')})

    def test_daemon_first_line(self):
        # Streaming output is still possible
        out = []
        proc = wait(gramex.cache.daemon(self.hello, first_line='hello', stream=out.append))
        [wait(future) for future in proc.wait_for_exit()]
        eq_(set(out), {self.msg('hello')})

        # Incorrect first line raises an error
        with assert_raises(AssertionError):
            proc = wait(gramex.cache.daemon(self.args, first_line='NOTHING'))
        [wait(future) for future in proc.wait_for_exit()]

        # Correct first line can be a string or regex
        proc = wait(gramex.cache.daemon(self.hello, first_line='hello'))
        [wait(future) for future in proc.wait_for_exit()]
        proc = wait(gramex.cache.daemon(self.args, first_line=re.compile(r'(OUT|ERR):\d\s*')))
        [wait(future) for future in proc.wait_for_exit()]
