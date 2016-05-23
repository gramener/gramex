'''
Debugging and profiling tools for Gramex
'''
import gc
import timeit
import inspect
import logging
import functools
try:
    import line_profiler
except ImportError:
    line_profiler = None


def _caller():
    '_caller() returns the "file:function:line" of the calling function'
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
        logging.info('%0.3fs %s %s', end - Context.start, msg, _caller())
        Context.start = end

    return timer


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
        logging.info('%0.3fs %s %s', end - self.start, self.msg, _caller())


if line_profiler is None:
    def line_profiler(func):
        logging.warn('@lineprofile requires line_profiler module')
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

timer = _make_timer()
