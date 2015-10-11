import datetime
import mimetypes
from pathlib import Path
from .transforms import build_transform
from tornado.web import HTTPError, RequestHandler


class FunctionHandler(RequestHandler):
    '''
    Renders the output of a function. It accepts these parameters when
    initialized:

    :arg string function: a string that resolves into any Python function or
        method (e.g. ``str.lower``). It is called as ``function(*args,
        **kwargs)``. By default, the result is rendered as-is (and hence must be
        a string.) If you ``redirect`` is specified, the result is discarded and
        the user is redirected to ``redirect``.
    :arg list args: positional arguments to be passed to the function.
    :arg dict kwargs: keyword arguments to be passed to the function.
    :arg dict headers: HTTP headers to set on the response.
    :arg string redirect: URL to redirect to when the result is done. Used to
        trigger calculations without displaying any output.

    Here's a simple use -- to display a string as a response to a URL. This
    configuration renders "Hello world" at the URL `/hello`::

        url:
          hello-world:
            pattern: /hello                             # The URL /hello
            handler: gramex.handlers.FunctionHandler    # Runs a function
            kwargs:
              function: six.text_type                   # Display as text in Python 2 & 3
              args:
                - Hello world                           # with "Hello world"

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

    If no ``args`` is specified, the Tornado `RequestHandler`_ is passed as the
    only positional argument. For example, in ``calculations.py``, add::

        def add(handler):
            return str(sum(float(x) for x in handler.get_arguments('x')))

    .. _RequestHandler: http://tornado.readthedocs.org/en/stable/web.html#request-handlers

    Now, the following configuration::

        function: calculations.add

    ... takes the URL ``?x=1&x=2&x=3`` to add up 1, 2, 3 and display ``6.0``.

    To redirect to a different URL when the function is done, use ``redirect``::

        function: module.calculation      # Run module.calculation(handler)
        redirect: /                       # and redirect to / thereafter
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
        result = self.function(self)
        for header_name, header_value in self.headers.items():
            self.set_header(header_name, header_value)
        if self.redirect_url is not None:
            self.redirect(self.redirect_url or self.request.headers.get('Referer', '/'))
        else:
            self.write(result)
            self.flush()


class DirectoryHandler(RequestHandler):
    '''
    Serves files with transformations. It accepts these parameters:

    :arg string path: The root directory from which files are served.
    :arg string default_filename: If the URL maps to a directory, this filename
        is displayed by default. For example, ``index.html`` or ``README.md``.
        The default is ``None``, which displays all files in the directory.
    :arg dict headers: HTTP headers to set on the response.
    :arg dict transform: Transformations that should be applied to the files.
        The key matches a `glob pattern`_ (e.g. ``'*.md'`` or ``'data/*'``.) The
        value is a dict with the same structure as :class:`FunctionHandler`,
        and accepts these keys:

        ``encoding``
            The encoding to load the file as.

        ``function``
            A string that resolves into any Python function or method (e.g.
            ``markdown.markdown``). By default, it is called as
            ``function(file_contents)`` and the result is rendered as-is (hence
            must be a string.)

        ``args``
            an optional list of positional arguments to be passed to the
            function. By default, this is just ``[_]`` where ``_`` is the file
            contents. For example, to pass the file contents as the second
            parameter, use ``args: [xx, _]``

        ``kwargs``:
            an optional list of keyword arguments to be passed to the function.
            ``_`` is replaced with the file contents.

        ``headers``:
            HTTP headers to set on the response.

    This example mimics SimpleHTTPServer_::

        pattern: /(.*)                              # Any URL
        handler: gramex.handlers.DirectoryHandler   # uses this handler
        kwargs:
            path: .                                 # shows files in the current directory
            default_filename: index.html            # Show index.html instead of directories
            index: true                             # List files if index.html doesn't exist

    To render Markdown as HTML, set up this handler::

        pattern: /blog/(.*)                         # Any URL starting with blog
        handler: gramex.handlers.DirectoryHandler   # uses this handler
        kwargs:
          path: blog/                               # Serve files from blog/
          default_filename: README.md               # using README.md as default
          transform:
            "*.md":                                 # Any file matching .md
              encoding: cp1252                      #   Open files with CP1252 encoding
              function: markdown.markdown           #   Convert from markdown to html
              kwargs:
                safe_mode: escape                   #   Pass safe_mode='escape'
                output_format: html5                #   Output in HTML5
              headers:
                Content-Type: text/html             #   MIME type: text/html

    .. _glob pattern: https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob
    .. _SimpleHTTPServer: https://docs.python.org/2/library/simplehttpserver.html
    '''

    SUPPORTED_METHODS = ("GET", "HEAD")

    def initialize(self, path, default_filename=None, index=None, headers={}, transform={}):
        self.root = Path(path).resolve()
        self.default_filename = default_filename
        self.index = index
        self.headers = headers
        self.transform = {}
        for pattern, trans in transform.items():
            self.transform[pattern] = {
                'function': build_transform(trans),
                'headers': trans.get('headers', {}),
                'encoding': trans.get('encoding'),
            }

    def head(self, path):
        return self.get(path, include_body=False)

    def get(self, path, include_body=True):
        self.path = (self.root / str(path)).absolute()
        # relative_to() raises ValueError if path is not under root
        self.path.relative_to(self.root)

        if self.path.is_dir():
            final_path = self.path / self.default_filename if self.default_filename else self.path
            if not (self.default_filename and final_path.exists()) and not self.index:
                raise HTTPError(404)
            # Ensure URL has a trailing '/' when displaying the index / default file
            if not self.request.path.endswith('/'):
                self.redirect(self.request.path + '/', permanent=True)
                return
        else:
            final_path = self.path
            if not final_path.exists():
                raise HTTPError(404)
            if not final_path.is_file():
                raise HTTPError(403, '%s is not a file or directory', self.path)

        if self.path.is_dir() and self.index and not (
                self.default_filename and final_path.exists()):
            self.set_header('Content-Type', 'text/html')
            content = [u'<h1>Index of %s </h1><ul>' % self.path]
            for path in self.path.iterdir():
                content.append(u'<li><a href="{name!s:s}">{name!s:s}{dir!s:s}</a></li>'.format(
                    name=path.relative_to(self.path),
                    dir='/' if path.is_dir() else ''))
            content.append(u'</ul>')
            self.content = ''.join(content)

        else:
            modified = final_path.stat().st_mtime
            self.set_header('Last-Modified', datetime.datetime.utcfromtimestamp(modified))

            mime_type, encoding = mimetypes.guess_type(str(final_path))
            if mime_type:
                self.set_header('Content-Type', mime_type)

            for header_name, header_value in self.headers.items():
                self.set_header(header_name, header_value)

            transform = {}
            for pattern, trans in self.transform.items():
                if final_path.match(pattern):
                    transform = trans
                    break
            encoding = transform.get('encoding', encoding)

            with final_path.open('r', encoding=encoding) as file:
                self.content = file.read()
                if transform:
                    for header_name, header_value in transform['headers'].items():
                        self.set_header(header_name, header_value)
                    self.content = transform['function'](self.content)
                self.set_header('Content-Length', len(self.content))

        if include_body:
            self.write(self.content)
