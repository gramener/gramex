'''
Debugging and profiling tools for Gramex
'''
import os
import gc
import timeit
import inspect
import functools
try:
    import line_profiler
except ImportError:
    line_profiler = None
from gramex.config import app_log


def _caller():
    '''_caller() returns the "file:function:line" of the calling function'''
    parent = inspect.getouterframes(inspect.currentframe())[2]
    return '[%s:%s:%d]' % (parent[1], parent[3], parent[2])


def _make_timer():
    '''
    This is used to create ``timer``. ``timer("msg")`` prints the time elapsed
    since the last timer call.
    '''
    class Context:
        start = timeit.default_timer()

    def timer(msg):
        end = timeit.default_timer()
        app_log.info('%0.3fs %s %s', end - Context.start, msg, _caller())
        Context.start = end

    return timer


# Create a single global instance of timer
timer = _make_timer()


class Timer(object):
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        self.start = timeit.default_timer()
        self.gc_old = gc.isenabled()

    def __exit__(self, type, value, traceback):
        end = timeit.default_timer()
        if self.gc_old:
            gc.enable()
        app_log.info('%0.3fs %s %s', end - self.start, self.msg, _caller())


if line_profiler is None:
    def lineprofile(func):
        app_log.warning('@lineprofile requires line_profiler module')
        return func
else:
    def lineprofile(func):
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
        TODO: flush the buffer
        '''
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
