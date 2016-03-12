import logging
import datetime
import mimetypes
from pathlib import Path
from tornado.escape import utf8
from ..transforms import build_transform
from tornado.web import HTTPError, RequestHandler


class DirectoryHandler(RequestHandler):
    '''
    Serves files with transformations. It accepts these parameters:

    :arg string path: The root directory from which files are served. Relative
        paths are specified from the base directory (where gramex starts from.)
        Use $source
    :arg string default_filename: If the URL maps to a directory, this filename
        is displayed by default. For example, ``index.html`` or ``README.md``.
        The default is ``None``, which displays all files in the directory.
    :arg dict headers: HTTP headers to set on the response.
    :arg dict transform: Transformations that should be applied to the files.
        The key matches a `glob pattern`_ (e.g. ``'*.md'`` or ``'data/*'``.) The
        value is a dict with the same structure as :class:`FunctionHandler`,
        and accepts these keys:

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

    This handler exposes the following ``pathlib.Path`` attributes:

    ``root``
        Root path for this handler. Same as the ``path`` argument
    ``path``
        Absolute Path requested by the user, without adding a default filename
    ``file``
        Absolute Path served to the user, after adding a default filename
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
                'function': build_transform(trans, vars=['content', 'handler'], args=['content']),
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
            self.file = self.path / self.default_filename if self.default_filename else self.path
            if not (self.default_filename and self.file.exists()) and not self.index:
                raise HTTPError(404)
            # Ensure URL has a trailing '/' when displaying the index / default file
            if not self.request.path.endswith('/'):
                self.redirect(self.request.path + '/', permanent=True)
                return
        else:
            self.file = self.path
            if not self.file.exists():
                raise HTTPError(404)
            if not self.file.is_file():
                raise HTTPError(403, '%s is not a file or directory', self.path)

        if self.path.is_dir() and self.index and not (
                self.default_filename and self.file.exists()):
            self.set_header('Content-Type', 'text/html')
            content = [u'<h1>Index of %s </h1><ul>' % self.path]
            for path in self.path.iterdir():
                # On Windows, pathlib on Python 2.7 won't handle Unicode. Ignore such files.
                # https://bitbucket.org/pitrou/pathlib/issues/25
                try:
                    content.append(u'<li><a href="{name!s:s}">{name!s:s}{dir!s:s}</a></li>'.format(
                        name=path.relative_to(self.path),
                        dir='/' if path.is_dir() else ''))
                except UnicodeDecodeError:
                    logging.warn("DirectoryHandler can't show unicode file {:s}".format(
                        repr(path)))
            content.append(u'</ul>')
            self.content = ''.join(content)

        else:
            modified = self.file.stat().st_mtime
            self.set_header('Last-Modified', datetime.datetime.utcfromtimestamp(modified))

            mime_type, content_encoding = mimetypes.guess_type(str(self.file))
            if mime_type:
                self.set_header('Content-Type', mime_type)

            for header_name, header_value in self.headers.items():
                self.set_header(header_name, header_value)

            transform = {}
            for pattern, trans in self.transform.items():
                if self.file.match(pattern):
                    transform = trans
                    break

            encoding = transform.get('encoding')
            with self.file.open('rb' if encoding is None else 'r', encoding=encoding) as file:
                self.content = file.read()
                if transform:
                    for header_name, header_value in transform['headers'].items():
                        self.set_header(header_name, header_value)
                    self.content = transform['function'](self.content, self)
                self.set_header('Content-Length', len(utf8(self.content)))

        if include_body:
            self.write(self.content)
