import io
import os
import six
import sys
import subprocess
import tornado.web
import tornado.gen
from threading import Thread, RLock
from tornado.concurrent import Future
from .basehandler import BaseHandler
from gramex.config import app_log


class ProcessHandler(BaseHandler):
    '''
    Runs sub-processes with transformations. It accepts these parameters:

    :arg list/string args: The first value is the command. The rest are optional
        string arguments. This is the same as in `Popen`_.
    :arg boolean shell: ``True`` passes the ``args`` through the shell, allowing
        wildcards like ``*``. If ``shell=True`` then use a single string for
        ``args`` that includes the arguments.
    :arg string cwd: Current working directory from where the command will run.
        Defaults to the same directory Gramex ran from.
    :arg string stdout: (**TODO**) The process output can be sent to:

        - ``pipe``: Display the (transformed) output. This is the default
        - ``false``: Ignore the output
        - ``filename.txt``: Save output to a ``filename.txt``

    :arg string stderr: The process error stream has the same options as stdout.
    :arg string stdin: (**TODO**)
    :arg int/string buffer: 'line' will write lines as they are generated.
        Numbers indicate the number of bytes to buffer. Defaults to
        ``io.DEFAULT_BUFFER_SIZE``.
    :arg string redirect: URL to redirect to when the result is done. Used to
        trigger calculations without displaying any output.
    :arg dict headers: HTTP headers to set on the response.
    :arg dict transform: (**TODO**)
        Transformations that should be applied to the files. The key matches a
        `glob pattern`_ (e.g. ``'*.md'`` or ``'data/*'``.) The value is a dict
        with the same structure as :class:`FunctionHandler`, and accepts these
        keys:

        ``encoding``
            The encoding to load the file as. If you don't specify an encoding,
            file contents are passed to ``function`` as a binary string.

        ``function``
            A string that resolves into any Python function or method (e.g.
            ``markdown.markdown``). By default, it is called with the file
            contents as ``function(content)`` and the result is rendered as-is
            (hence must be a string.)

        ``args``
            optional positional arguments to be passed to the function. By
            default, this is just ``['content']`` where ``content`` is the file
            contents. You can also pass the handler via ``['handler']``, or both
            of them in any order.

        ``kwargs``:
            an optional list of keyword arguments to be passed to the function.
            A value with of ``handler`` and ``content`` is replaced with the
            RequestHandler and file contents respectively.

        ``headers``:
            HTTP headers to set on the response.

    .. _Popen: https://docs.python.org/3/library/subprocess.html#subprocess.Popen

    '''
    @classmethod
    def setup(cls, args, shell=False, cwd=None, buffer=0, redirect=None, headers={}, **kwargs):
        super(ProcessHandler, cls).setup(**kwargs)
        cls.args = args
        cls.shell = shell
        cls.redirect = redirect
        cls._write_lock = RLock()
        cls.buffer_size = buffer
        # Normalize current directory for path, if provided
        cls.cwd = cwd if cwd is None else os.path.abspath(cwd)
        # File handles for stdout/stderr are cached in cls.handles
        cls.handles = {}

        cls.headers = headers
        cls.post = cls.get

    def stream_callbacks(self, targets, name):
        # stdout/stderr are can be specified as a scalar or a list.
        # Convert it into a list of callback fn(data)

        # if no target is specified, stream to RequestHandler
        if targets is None:
            targets = ['pipe']
        # if a string is specified, treat it as the sole file output
        elif not isinstance(targets, list):
            targets = [targets]

        callbacks = []
        for target in targets:
            # pipe write to the RequestHandler
            if target == 'pipe':
                callbacks.append(self._write)
            # false-y values are ignored. (False, 0, etc)
            elif not target:
                pass
            # strings are treated as files
            elif isinstance(target, six.string_types):
                # cache file handles for re-use between stdout, stderr
                if target not in self.handles:
                    self.handles[target] = io.open(target, mode='wb')
                handle = self.handles[target]
                callbacks.append(handle.write)
            # warn on unknown parameters (e.g. numbers, True, etc)
            else:
                app_log.warn('ProcessHandler: %s: %s is not implemented' % (name, target))
        return callbacks

    def initialize(self, stdout=None, stderr=None, stdin=None, **kwargs):
        super(ProcessHandler, self).initialize(**kwargs)
        self.stream_stdout = self.stream_callbacks(stdout, name='stdout')
        self.stream_stderr = self.stream_callbacks(stderr, name='stderr')

    @tornado.gen.coroutine
    def get(self, *path_args):
        for header_name, header_value in self.headers.items():
            self.set_header(header_name, header_value)

        proc = _Subprocess(
            self.args,
            shell=self.shell,
            cwd=self.cwd,
            stream_stdout=self.stream_stdout,
            stream_stderr=self.stream_stderr,
            buffer_size=self.buffer_size,
        )
        yield proc.wait_for_exit()
        # Wait for process to finish
        proc.proc.wait()

    def _write(self, data):
        with self._write_lock:
            self.write(data)
            self.flush()

    def on_finish(self):
        'Close all open handles after the request has finished'
        for target, handle in self.handles.items():
            handle.close()


class _Subprocess(object):
    '''
    tornado.process.Subprocess does not work on Windows.
    https://github.com/tornadoweb/tornado/issues/1585

    This is a threaded alternative based on
    http://stackoverflow.com/a/4896288/100904

    Create an internal implementation that works. You can later expose it.
    Don't worry about Tornado conventions. Just get it to work first.

        proc = _Subprocess(
            args,
            on_stdout=[self._write],
            on_stderr=[self._write],
            **kwargs
        )
        yield proc.wait_for_exit()

    '''
    def __init__(self, args, stream_stdout=[], stream_stderr=[], buffer_size=0, **kwargs):
        self.args = args

        # self.proc.stdout & self.proc.stderr are streams with process output
        kwargs['stdout'] = kwargs['stderr'] = subprocess.PIPE

        # On UNIX, close all file descriptors except 0, 1, 2 before child
        # process is executed. I've no idea why. Copied from
        # http://stackoverflow.com/a/4896288/100904
        kwargs['close_fds'] = 'posix' in sys.builtin_module_names

        if hasattr(buffer_size, 'lower') and 'line' in buffer_size.lower():
            def _write(stream, callbacks, future):
                'Call callbacks with content from stream. On EOF mark future as done'
                while True:
                    content = stream.readline()
                    if len(content) > 0:
                        for callback in callbacks:
                            callback(content)
                    else:
                        stream.close()
                        future.set_result('')
                        break
        else:
            # If the buffer size is 0 or negative, use the default buffer size to read
            if buffer_size <= 0:
                buffer_size = io.DEFAULT_BUFFER_SIZE

            def _write(stream, callbacks, future):
                'Call callbacks with content from stream. On EOF mark future as done'
                while True:
                    content = stream.read(buffer_size)
                    size = len(content)
                    if size > 0:
                        for callback in callbacks:
                            callback(content)
                    if size < buffer_size:
                        stream.close()
                        future.set_result('')
                        break

        self.proc = subprocess.Popen(args, **kwargs)
        self.thread = {}        # Has the running threads
        self.future = {}        # Stores the futures indicating stream close
        callbacks = {
            'stdout': stream_stdout,
            'stderr': stream_stderr,
        }
        for stream in ('stdout', 'stderr'):
            self.future[stream] = f = Future()
            # Thread writes from self.proc.stdout / stderr to appropriate callbacks
            self.thread[stream] = t = Thread(
                target=_write,
                args=(getattr(self.proc, stream), callbacks[stream], f),
            )
            t.daemon = True     # Thread dies with the program
            t.start()

    def wait_for_exit(self):
        return list(self.future.values())
