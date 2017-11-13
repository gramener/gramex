'''
Debugging and profiling tools for Gramex
'''
from __future__ import print_function, unicode_literals

import os
import gc
import six
import sys
import pprint
import timeit
import inspect
import logging
import functools
from trace import Trace
try:
    import line_profiler
except ImportError:
    line_profiler = None
from gramex.config import app_log


def _indent(text, prefix, predicate=None):
    '''Backport of textwrap.indent for Python 2.7'''
    if predicate is None:
        def predicate(line):
            return line.strip()

    def prefixed_lines():
        for line in text.splitlines(True):
            yield (prefix + line if predicate(line) else line)
    return ''.join(prefixed_lines())


def _caller():
    '''_caller() returns the "file:function:line" of the calling function'''
    parent = inspect.getouterframes(inspect.currentframe())[2]
    return '[%s:%s:%d]' % (parent[1], parent[3], parent[2])


class Timer(object):
    '''
    Find how long a code blocks takes to execute. Wrap any code block like this::

        >>> from gramex.debug import Timer
        >>> with Timer('optional message'):
        >>>     slow_running_code()
        WARNING:gramex:1.000s optional message [<file>:<func>:line]
    '''
    def __init__(self, msg='', level=logging.WARNING):
        self.msg = msg
        self.level = logging.WARNING

    def __enter__(self):
        self.start = timeit.default_timer()
        self.gc_old = gc.isenabled()

    def __exit__(self, type, value, traceback):
        end = timeit.default_timer()
        if self.gc_old:
            gc.enable()
        app_log.log(self.level, '%0.3fs %s %s', end - self.start, self.msg, _caller())


def _write(obj, prefix=None, stream=sys.stdout):
    text = pprint.pformat(obj, indent=4)
    if prefix is None:
        stream.write(_indent(text, ' .. '))
    else:
        text = _indent(text, ' .. ' + ' ' * len(prefix) + '   ')
        stream.write(' .. ' + prefix + ' = ' + text[7 + len(prefix):])
    stream.write('\n')


def print(*args, **kwargs):             # noqa
    '''
    A replacement for the ``print`` function that also logs the (file, function,
    line, msg) from where it is called. For example::

        >>> from __future__ import print_function       # required for Python 2.x
        >>> from gramex.debug import print              # import print function
        >>> print('hello world')                        # It works like the print function
        <file>(line).<function>: hello world
        >>> print(x=1, y=2)                             # Use kwargs to print variable names
        <file>(line).<function>:
         .. x = 1
         .. y = 2

    It automatically pretty-prints complex variables.
    '''
    stream = kwargs.pop('stream', sys.stdout)
    parent = inspect.getouterframes(inspect.currentframe())[1]
    file, line, function = parent[1:4]
    if len(args) == 1 and not kwargs:
        stream.write('{}({}).{}: {}\n'.format(file, line, function, args[0]))
    else:
        stream.write('\n{}({}).{}:\n'.format(file, line, function))
        for val in args:
            _write(val, stream=stream)
        for key, val in kwargs.items():
            _write(val, key, stream=stream)
        stream.write('\n')


def trace(trace=True, exclude=None, **kwargs):
    '''
    Decorator to trace line execution. Usage::

        @trace()
        def method(...):
            ...

    When ``method()`` is called, every line of execution is traced.
    '''
    if exclude is None:
        ignoredirs = (sys.prefix, )
    elif isinstance(exclude, six.string_types):
        ignoredirs = (sys.prefix, os.path.abspath(exclude))
    elif isinstance(exclude, (list, tuple)):
        ignoredirs = [sys.prefix] + [os.path.abspath(path) for path in exclude]
    tracer = Trace(trace=trace, ignoredirs=ignoredirs, **kwargs)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return tracer.runfunc(func, *args, **kwargs)
        return wrapper

    return decorator


if line_profiler is None:
    def lineprofile(func):
        app_log.warning('@lineprofile requires line_profiler module')
        return func
else:
    def lineprofile(func):
        '''
        A decorator that prints the time taken for each line of a function every
        time it is called. This example prints each line's performance::

            >>> from gramex.debug import lineprofile
            >>> @lineprofile
            >>> def calc():
            >>>     ...
        '''
        profile = line_profiler.LineProfiler(func)

        @functools.wraps(func)
        def wrapper(*args, **kwds):
            profile.enable_by_count()
            try:
                result = func(*args, **kwds)
            finally:
                profile.disable_by_count()
            profile.print_stats(stripzeros=True)
            return result
        return wrapper


# Windows
if os.name == 'nt':
    import msvcrt

    def getch():
        '''
        Return character if something was typed on the console, else None.
        Used internally by Gramex on the command line.
        '''
        # TODO: flush the buffer
        return msvcrt.getch() if msvcrt.kbhit() else None

# Posix (Linux, OS X)
else:
    import sys
    import termios
    import atexit
    from select import select

    if sys.__stdin__.isatty():
        def _init_non_blocking_terminal():
            fd = sys.__stdin__.fileno()
            old_term = termios.tcgetattr(fd)
            # Support normal-terminal reset at exit
            atexit.register(lambda: termios.tcsetattr(fd, termios.TCSAFLUSH, old_term))

            # New terminal setting unbuffered
            new_term = termios.tcgetattr(fd)
            new_term[3] = (new_term[3] & ~termios.ICANON & ~termios.ECHO)
            termios.tcsetattr(fd, termios.TCSAFLUSH, new_term)

        def getch():
            '''
            Return character if something was typed on the console, else None.
            TODO: flush the buffer
            '''
            dr, dw, de = select([sys.stdin], [], [], 0)
            if dr != []:
                return sys.stdin.read(1)
            else:
                return None

        _init_non_blocking_terminal()

    else:
        def getch():
            return None


def _make_timer():
    '''
    ``timer("msg")`` prints the time elapsed since the last timer call::

        >>> from gramex.debug import timer
        >>> gramex.debug.timer('abc')
        WARNING:gramex:7.583s abc [<file>:<function>:1]     # Time since Gramex start
        >>> gramex.debug.timer('def')
        WARNING:gramex:3.707s def [<file>:<function>:1]     # Time since last call
    '''
    class Context:
        start = timeit.default_timer()

    def timer(msg, level=logging.WARNING):
        end = timeit.default_timer()
        app_log.log(level, '%0.3fs %s %s', end - Context.start, msg, _caller())
        Context.start = end

    timer.__doc__ = _make_timer.__doc__
    return timer


timer = _make_timer()
