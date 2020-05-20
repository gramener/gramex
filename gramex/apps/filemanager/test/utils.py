from gramex.config import app_log
from gramex.cache import Subprocess
from tornado.gen import coroutine


@coroutine
def test():
    out = []
    proc = Subprocess(
        ['npm', 'test'],
        stream_stdout=[out.append],
        stream_stderr=[out.append],
        buffer_size='line'
    )
    yield proc.wait_for_exit()
    for c in out:
        line = c.decode('utf8').rstrip().lstrip()
        if line:
            app_log.debug(line)
