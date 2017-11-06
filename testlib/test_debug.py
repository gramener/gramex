from __future__ import print_function

import os
import inspect
import unittest
from io import StringIO
from textwrap import dedent
import gramex.debug
from gramex.debug import timer, Timer
from testfixtures import LogCapture
from nose.tools import eq_


def line_no():
    '''Returns current line number in file where it is called'''
    parent = inspect.getouterframes(inspect.currentframe())[1]
    return parent[2]


def p(*args, **kwargs):
    return gramex.debug.print(*args, **kwargs)      # noqa


class TestPrint(unittest.TestCase):
    def test_single(self):
        stream = StringIO()
        p('x', stream=stream)
        line = line_no() - 1
        val = stream.getvalue()
        eq_(val, __file__ + '(%d).test_single: x\n' % line)

    def test_kwarg(self):
        stream = StringIO()
        p(val=[10, 20, 30], stream=stream)
        line = line_no() - 1
        val = stream.getvalue()
        eq_(val, '\n' + __file__ + '(%d).test_kwarg:\n .. val = [10, 20, 30]\n\n' % line)

    def test_multi(self):
        stream = StringIO()
        p(a=True, b=1, lst=[1, 2], string='abc', stream=stream)
        line = line_no() - 1
        val = stream.getvalue()
        eq_(val, dedent('''
            {}({:d}).test_multi:
             .. a = True
             .. b = 1
             .. lst = [1, 2]
             .. string = 'abc'

            ''').format(__file__, line))


class TestDebug(unittest.TestCase):
    def test_timer(self):
        with LogCapture() as logs:
            timer('start')
            timer('middle')
        args = [rec.args for rec in logs.records
                if len(rec.args) > 2 and 'test_debug.py:test_timer' in rec.args[2]]
        eq_(len(args), 2)
        eq_([arg[1] for arg in args], ['start', 'middle'])
        eq_(
            [arg[2].split(os.sep)[-1].rsplit(':', 1)[0] for arg in args],
            ['test_debug.py:test_timer', 'test_debug.py:test_timer'])

        with LogCapture() as logs:
            with Timer('msg'):
                pass
        args = [rec.args for rec in logs.records
                if len(rec.args) > 2 and 'test_debug.py:test_timer' in rec.args[2]]
        eq_(len(args), 1)
        eq_([arg[1] for arg in args], ['msg'])
        eq_(
            [arg[2].split(os.sep)[-1].rsplit(':', 1)[0] for arg in args],
            ['test_debug.py:test_timer'])
