import io
import os
import six
import tornado.web
import tornado.gen
from threading import RLock
from .basehandler import BaseHandler
from gramex.config import app_log
from gramex.cache import Subprocess


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
    :arg string stdout: The process output can be sent to:

        - ``pipe``: Display the (transformed) output. This is the default
        - ``false``: Ignore the output
        - ``filename.txt``: Save output to a ``filename.txt``

    :arg string stderr: The process error stream has the same options as stdout.
    :arg string stdin: (**TODO**)
    :arg int/string buffer: 'line' will write lines as they are generated.
        Numbers indicate the number of bytes to buffer. Defaults to
        ``io.DEFAULT_BUFFER_SIZE``.
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
    def setup(cls, args, shell=False, cwd=None, buffer=0, headers={}, **kwargs):
        super(ProcessHandler, cls).setup(**kwargs)
        cls.cmdargs = args
        cls.shell = shell
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
                app_log.warning('ProcessHandler: %s: %s is not implemented' % (name, target))
        return callbacks

    def initialize(self, stdout=None, stderr=None, stdin=None, **kwargs):
        super(ProcessHandler, self).initialize(**kwargs)
        self.stream_stdout = self.stream_callbacks(stdout, name='stdout')
        self.stream_stderr = self.stream_callbacks(stderr, name='stderr')

    @tornado.gen.coroutine
    def get(self, *path_args):
        if self.redirects:
            self.save_redirect_page()
        for header_name, header_value in self.headers.items():
            self.set_header(header_name, header_value)

        proc = Subprocess(
            self.cmdargs,
            shell=self.shell,
            cwd=self.cwd,
            stream_stdout=self.stream_stdout,
            stream_stderr=self.stream_stderr,
            buffer_size=self.buffer_size,
        )
        yield proc.wait_for_exit()
        # Wait for process to finish
        proc.proc.wait()
        if self.redirects:
            self.redirect_next()

    def _write(self, data):
        with self._write_lock:
            self.write(data)
            # Flush every time. This disables Etag, but processes have
            # side-effects, so we should not be caching these requests anyway.
            self.flush()

    def on_finish(self):
        '''Close all open handles after the request has finished'''
        for target, handle in self.handles.items():
            handle.close()
        super(ProcessHandler, self).on_finish()
