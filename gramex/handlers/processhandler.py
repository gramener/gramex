import io
import os
import tornado.web
import tornado.gen
from threading import RLock
from typing import Union, List
from .basehandler import BaseHandler
from gramex.config import app_log
from gramex.cache import Subprocess


class ProcessHandler(BaseHandler):
    @classmethod
    def setup(
        cls,
        args: Union[List[str], str],
        shell: bool = False,
        cwd: str = None,
        buffer: Union[str, int] = 0,
        headers: dict = {},
        **kwargs,
    ):
        '''Set up handler to stream process output.

        Parameters:

            args: The first value is the command. The rest are optional string arguments.
                Same as `subprocess.Popen()`.
            shell: `True` passes the `args` through the shell, allowing wildcards like `*`.
                If `shell=True` then use a single string for `args` that includes the arguments.
            cwd: Current working directory from where the command will run.
                Defaults to the same directory Gramex ran from.
            buffer: Number of bytes to buffer. Defaults: `io.DEFAULT_BUFFER_SIZE`. Or `"line"`
                to buffer by newline.
            headers: HTTP headers to set on the response.
        '''
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
            elif isinstance(target, (str, bytes)):
                # cache file handles for re-use between stdout, stderr
                if target not in self.handles:
                    self.handles[target] = io.open(target, mode='wb')
                handle = self.handles[target]
                callbacks.append(handle.write)
            # warn on unknown parameters (e.g. numbers, True, etc)
            else:
                app_log.warning(f'ProcessHandler: {name}: {target} is not implemented')
        return callbacks

    def initialize(
        self,
        stdout: Union[List[str], str] = None,
        stderr: Union[List[str], str] = None,
        stdin: Union[List[str], str] = None,
        **kwargs,
    ):
        '''Sets up I/O stream processing.

        Parameters:

            stdout: The process output can be sent to
            stderr: The process error stream has the same options as stdout.
            stdin: (**TODO**)

        `stdout`, `stderr` and `stdin` can be one of the below, or a list of the below:

        - `"pipe"`: Display the (transformed) output. This is the default
        - `"false"`: Ignore the output
        - `"filename.txt"`: Save output to a `filename.txt`
        '''
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
            # NOTE: developer should sanitize args if shell=True
            # B604 any_other_function_with_shell_equals_true
            shell=self.shell,  # noqa S604
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
        for handle in self.handles.values():
            handle.close()
        super(ProcessHandler, self).on_finish()
