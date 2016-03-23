import os
from tornado.web import RequestHandler


class ProcessHandler(RequestHandler):
    '''
    Runs a process asynchronously and renders its output. It accepts these
    parameters when initialized:

    :arg string process: path to the executable.
    :arg list args: positional arguments to be passed to the function.
    :arg dict headers: HTTP headers to set on the response.
    :arg string redirect: URL to redirect to when the result is done. Used to
        trigger calculations without displaying any output.

    Here's a simple example that lists files in a directory. For example,
    `/list?path=/tmp&sort=size`::

        url:
          list:
            pattern: /list                              # The URL /list
            handler: gramex.handlers.ProcessHandler     # Runs a process
            kwargs:
              process: /usr/bin/ls                      # Listing a directory
              args:
                - "-la"                                 # Long listing
                - "=handler.get_argument('path', '')"   # of path
                - "=--sort=handler.get_argument('sort', 'none')"
              headers:
                Content-Type: text/plain                # Printed as text
    '''
    def initialize(self, **kwargs):
        if 'process' not in kwargs:
            raise KeyError('No process for ProcessHandler')
        self.process = kwargs['process']
        if not os.path.exists(self.process):
            raise OSError('No file %s for ProcessHandler to run' % self.process)

    def get(self, *path_args):
        pass

    def post(self, *path_args):
        pass
