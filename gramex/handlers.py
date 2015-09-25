import os
from pathlib import Path
from .transforms import build_transform
from tornado.web import HTTPError, RequestHandler, StaticFileHandler


class FunctionHandler(RequestHandler):
    '''
    Renders the output of a function. It accepts these parameters when
    initialized:

    :arg string function: a string that resolves into any Python function or
        method (e.g. ``string.lower``). It is called as ``function(*args,
        **kwargs)``. By default, the result is rendered as-is (and hence must be
        a string.) If you ``redirect`` is specified, the result is discarded and
        the user is redirected to ``redirect``.
    :arg list args: positional arguments to be passed to the function.
    :arg dict kwargs: keyword arguments to be passed to the function.
    :arg dict headers: headers to set on the response.
    :arg string redirect: URL to redirect to when the result is done. Used to
        trigger calculations without displaying any output.

    Here's a simple use -- to display a string as a response to a URL. This
    configuration renders "Hello world" at the URL `/hello`::

        function: six.text_type               # Display as text in Python 2 & 3
        args:
          - Hello world                       # with "Hello world"

    Only a single function call is allowed. To chain function calls or to do
    anything more complex, create a Python function and call that instead. For
    example, create a ``calculations.py`` with this method::

        import json
        def total(*items):
            'Calculate total of all items and render as JSON: value and string'
            total = sum(float(item) for item in items)
            return json.dumps({
                'display': '${:,.2f}'.format(total),
                'value': total,
            })

    Now, you can use this configuration::

        function: calculations.total
        args: [100, 200.0, 300.00]
        headers:
          Content-Type: application/json

    ... to get this result in JSON:

        {"display": "$600.00", "value": 600.0}

    **TODO**: extend function to use URL query parameters
    '''
    def initialize(self, function, args=None, kwargs=None, headers={}, redirect=None):
        self.function = build_transform({
            'function': function,
            'args': ['_'] if args is None else args,
            'kwargs': {} if kwargs is None else kwargs
        })
        self.headers = headers
        self.redirect_url = redirect

    def get(self):
        result = self.function('')
        for header_name, header_value in self.headers.items():
            self.set_header(header_name, header_value)
        if self.redirect_url is not None:
            self.redirect(self.redirect_url or self.request.headers.get('Referer', '/'))
        else:
            self.write(result)
            self.flush()


class DirectoryHandler(StaticFileHandler):
    '''
    Serves files in a directory like `StaticFileHandler`_, but lists files in
    the directory if the `default_filename` is missing. This behaviour is like
    `SimpleHTTPServer`_.

    The usage is otherwise identical to `StaticFileHandler`_.

    .. _SimpleHTTPServer: https://docs.python.org/2/library/simplehttpserver.html
    .. _StaticFileHandler:
       http://tornado.readthedocs.org/en/latest/web.html#tornado.web.StaticFileHandler
    '''

    def validate_absolute_path(self, root, absolute_path):
        '''
        Return directory itself for directory
        '''
        root = os.path.abspath(root) + os.path.sep
        # The trailing slash also needs to be temporarily added back
        # the requested path so a request to root/ will match.
        if not (absolute_path + os.path.sep).startswith(root):
            raise HTTPError(403, "%s is not in root static directory",
                            self.path)
        if os.path.isdir(absolute_path):
            if not self.request.path.endswith("/"):
                self.redirect(self.request.path + "/", permanent=True)
                return
            if self.default_filename is not None:
                default_file = os.path.join(absolute_path, self.default_filename)
                if os.path.isfile(default_file):
                    return default_file
            # Now, we have a directory ending with "/" without a
            # default_filename, so just allow it.
            return absolute_path
        if not os.path.exists(absolute_path):
            raise HTTPError(404)
        if not os.path.isfile(absolute_path):
            raise HTTPError(403, "%s is not a file", self.path)
        return absolute_path

    @classmethod
    def get_content(cls, abspath, start=None, end=None):
        '''
        Return contents of the file at ``abspath`` from ``start`` byte to
        ``end`` byte. If the file is missing and the ``default_filename`` is
        also missing, render the directory index instead.
        '''
        if os.path.isdir(abspath):
            content = ['<h1>Index of %s </h1><ul>' % abspath]
            for name in os.listdir(abspath):
                content.append('<li><a href="%s">%s</a></li>' % (name, name))
            content.append('</ul>')
        else:
            content = super(DirectoryHandler, cls).get_content(abspath, start, end)
        if not isinstance(content, bytes):
            content = ''.join(content)
        return content

    def get_content_size(self):
        'Return the size of the requested file in bytes'
        if os.path.isdir(self.absolute_path):
            return len(self.get_content(self.absolute_path))
        return super(DirectoryHandler, self).get_content_size()

    def get_content_type(self):
        'Return the MIME type of the requested file in bytes'
        if os.path.isdir(self.absolute_path):
            return 'text/html'
        return super(DirectoryHandler, self).get_content_type()


class TransformHandler(RequestHandler):
    '''
    Renders files in a path after transforming them. This is useful for a static
    file handler that pre-processes responses. Here are some examples::

        pattern: /help/(.*)
        handler: gramex.handlers.TransformHandler   # This handler
        kwargs:
          path: help/                               # Serve files from help/
          default_filename: index.yaml              # Directory index file
          transform:
            "*.md":                                 # Any file matching .md
              transform: markdown.markdown          #   Convert .md to html
              headers:
                Content-Type: text/html             #   MIME type: text/html
            "*.yaml":                               # YAML files use BadgerFish
              transform: gramex.transforms.badgerfish
              headers:
                Content-Type: text/html             #   MIME type: text/html
            "*.lower":                              # Any .lower file
              transform: string.lower               #   Convert to lowercase
              headers:
                Content-Type: text/plain            #   Serve as plain text
    '''
    def initialize(self, path, default_filename=None, transform={}):
        self.root = path
        self.default_filename = default_filename
        self.transform = {}
        for pattern, trans in transform.items():
            self.transform[pattern] = {
                'function': build_transform(trans),
                'headers': trans.get('headers', {})
            }

    def get(self, path):
        self.path = path
        if os.path.sep != '/':
            self.path = self.path.replace('/', os.path.sep)
        absolute_path = os.path.abspath(os.path.join(self.root, self.path))

        if (os.path.isdir(absolute_path) and
                self.default_filename is not None):
            if not self.request.path.endswith("/"):
                self.redirect(self.request.path + "/", permanent=True)
                return
            absolute_path = os.path.join(absolute_path, self.default_filename)
        if not os.path.exists(absolute_path):
            raise HTTPError(404)
        if not os.path.isfile(absolute_path):
            raise HTTPError(403, "%s is not a file", self.path)

        # Python 2.7 pathlib only accepts str, not unicode
        path = Path(str(absolute_path))
        with path.open('r+b') as handle:
            content = handle.read()

        # Apply first matching transforms
        for pattern, trans in self.transform.items():
            if path.match(pattern):
                content = trans['function'](content)
                for header_name, header_value in trans['headers'].items():
                    self.set_header(header_name, header_value)
                break

        self.write(content)
        self.flush()
