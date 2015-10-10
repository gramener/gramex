import os
import hashlib
from pathlib import Path
from .transforms import build_transform
from tornado.web import HTTPError, RequestHandler, StaticFileHandler
from tornado.util import bytes_type


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


class DirectoryHandler(StaticFileHandler):
    '''
    Serves files with transformations. It accepts these parameters:

    :arg string path: The root directory from which files are served.
    :arg string default_filename: If the URL maps to a directory, this filename
        is displayed by default. For example, ``index.html`` or ``README.md``.
        The default is ``None``, which displays all files in the directory.
    :arg dict transform: Transformations that should be applied to the files.
        The key matches a `glob pattern`_ (e.g. ``'*.md'`` or ``'data/*'``.) The
        value is a dict with the same structure as :class:`FunctionHandler`,
        with keys ``function``, ``headers``, etc. The ``function`` parameter is
        passed the `RequestHandler`_ by default. The handler's ``.content``
        attribute has the file contents.s

    This example mimics SimpleHTTPServer_::

        pattern: /(.*)                              # Any URL
        handler: gramex.handlers.DirectoryHandler   # uses this handler
        kwargs:
            path: .                                 # shows files in the current directory
            default_filename: index.html            # Show index.html instead of directories

    To render Markdown as HTML, create this ``blog.py``::

        from markdown import markdown
        def to_markdown(handler, **kwargs):
            return markdown(handler.content, **kwargs)

    ... and set up the handlers::

        pattern: /blog/(.*)                         # Any URL starting with blog
        handler: gramex.handlers.DirectoryHandler   # uses this handler
        kwargs:
          path: blog/                               # Serve files from blog/
          default_filename: README.md               # using README.md as default
          transform:
            "*.md":                                 # Any file matching .md
              function: blog.to_markdown            #   Convert .md to html
              kwargs:
                safe_mode: escape                   #   Pass safe_mode='escape'
                output_format: html5                #   Output in HTML5
              headers:
                Content-Type: text/html             #   MIME type: text/html

    .. _glob pattern: https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob
    .. _SimpleHTTPServer: https://docs.python.org/2/library/simplehttpserver.html
    .. _StaticFileHandler:
       http://tornado.readthedocs.org/en/latest/web.html#tornado.web.StaticFileHandler

    This method inherits from Tornado's StaticFileHandler_,
    '''

    def initialize(self, path, default_filename=None, transform={}):
        super(DirectoryHandler, self).initialize(path, default_filename)
        self.transform = {}
        for pattern, trans in transform.items():
            self.transform[pattern] = {
                'function': build_transform(trans),
                'headers': trans.get('headers', {})
            }

    def validate_absolute_path(self, root, absolute_path):
        # If absolute_path is a directory, return it as-is.
        # Otherwise same as StaticFileHandler.validate_absolute_path
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

    def get_transform(self, abspath):
        '''
        Return the first applicable transform for the absolute path.
        Else return ``False``.

        The returned ``transform`` has a callable ``function`` that is called
        with the handler.
        '''
        if not hasattr(self, '_current_transform'):
            self._current_transform = False
            path = Path(str(abspath))
            for pattern, trans in self.transform.items():
                if path.match(pattern):
                    self._current_transform = trans
                    break
        return self._current_transform

    def get_content(self, abspath, start=None, end=None):
        '''
        Return contents of the file at ``abspath`` from ``start`` byte to
        ``end`` byte. If the file is missing and the ``default_filename`` is
        also missing, render the directory index instead (ignoring start/end.)

        The result is a byte-string or a byte-string generator
        '''
        if os.path.isdir(abspath):
            content = [u'<h1>Index of %s </h1><ul>' % abspath]
            for name in os.listdir(abspath):
                isdir = u'/' if os.path.isdir(os.path.join(abspath, name)) else ''
                content.append(u'<li><a href="%s">%s%s</a></li>' % (name, name, isdir))
            content.append(u'</ul>')
            return u''.join(content).encode('utf-8')
        else:
            content = super(DirectoryHandler, self).get_content(abspath, start, end)
            transform = self.get_transform(abspath)
            if transform:
                for header_name, header_value in transform['headers'].items():
                    self.set_header(header_name, header_value)
                if not hasattr(self, 'content'):
                    self.content = (content if isinstance(content, bytes_type)
                                    else bytes_type().join(content))
                    self.content = transform['function'](self)
                return self.content
            return content

    def get_content_version(self, abspath):
        'Returns version string for the resource at the given path'
        data = self.get_content(abspath)
        hasher = hashlib.md5()
        if isinstance(data, bytes_type):
            hasher.update(data)
        else:
            for chunk in data:
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_content_size(self):
        'Return the size of the requested file in bytes'
        if os.path.isdir(self.absolute_path) or self.get_transform(self.absolute_path):
            return len(self.get_content(self.absolute_path))
        else:
            return super(DirectoryHandler, self).get_content_size()

    def _get_cached_version(self, abs_path):
        with self._lock:
            hashes = self._static_hashes
            if abs_path not in hashes:
                hashes[abs_path] = self.get_content_version(abs_path)
            hsh = hashes.get(abs_path)
            if hsh:
                return hsh
        return None
