import re
import inspect
import unittest
from io import StringIO
import gramex.debug
from gramex.debug import timer, Timer
from testfixtures import LogCapture
from nose.tools import eq_, ok_

testfile = __file__.replace('.pyc', '.py')


def line_no():
    '''Returns current line number in file where it is called'''
    parent = inspect.getouterframes(inspect.currentframe())[1]
    return parent[2]


class TestPrint(unittest.TestCase):
    def test_single(self):
        stream = StringIO()
        gramex.debug.print('x', stream=stream)      # noqa
        line = line_no() - 1
        val = stream.getvalue().replace('.pyc', '.py')
        eq_(val, testfile + '(%d).test_single: x\n' % line)

    def test_kwarg(self):
        stream = StringIO()
        gramex.debug.print(val=[10, 20, 30], stream=stream)     # noqa
        line = line_no() - 1
        val = stream.getvalue().replace('.pyc', '.py')
        eq_(val, '\n' + testfile + '(%d).test_kwarg:\n .. val = [10, 20, 30]\n\n' % line)

    def test_multi(self):
        stream = StringIO()
        gramex.debug.print(a=True, b=1, lst=[1, 2], string='abc', stream=stream)    # noqa
        line = line_no() - 1
        val = stream.getvalue().replace('.pyc', '.py')
        ok_(val.startswith('\n'))
        ok_(val.endswith('\n'))
        lines = {line for line in stream.getvalue().splitlines()}
        self.assertIn('{}({:d}).test_multi:'.format(testfile, line), lines)
        self.assertIn(" .. a = True", lines)
        self.assertIn(" .. b = 1", lines)
        self.assertIn(" .. lst = [1, 2]", lines)
        self.assertIn(" .. string = 'abc'", lines)


class TestDebug(unittest.TestCase):
    def test_timer(self):
        with LogCapture() as logs:
            timer('start')
            timer('middle')
        args = [rec.msg for rec in logs.records if 'test_debug.py:test_timer' in rec.msg]
        eq_(len(args), 2)
        ok_(re.search(r'start.*test_debug.py:test_timer', args[0]))
        ok_(re.search(r'middle.*test_debug.py:test_timer', args[1]))

        with LogCapture() as logs:
            with Timer('msg'):
                pass
        args = [rec.msg for rec in logs.records if 'test_debug.py:test_timer' in rec.msg]
        eq_(len(args), 1)
        ok_(re.search(r'msg.*test_debug.py:test_timer', args[0]))
