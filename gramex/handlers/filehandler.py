import string
import logging
import datetime
import mimetypes
import tornado.web
import tornado.gen
from pathlib import Path
from tornado.escape import utf8
from tornado.web import HTTPError
from .basehandler import BaseHandler
from ..transforms import build_transform


# Directory indices are served using this template by default
_template_path = Path(__file__).absolute().parent / 'filehandler.template.html'
with _template_path.open(encoding='utf-8') as handle:
    dir_template = string.Template(handle.read())


class FileHandler(BaseHandler):
    '''
    Serves files with transformations. It accepts these parameters:

    :arg string path: Can be one of three things:

        - The filename to serve. For all files matching the pattern, this
          filename is returned.
        - The root directory from which files are served. The first parameter of
          the URL pattern is the file path under this directory. Relative paths
          are specified from where gramex was run.
        - A list of files to serve. These files are concatenated and served one
          after the other.

    :arg string default_filename: If the URL maps to a directory, this filename
        is displayed by default. For example, ``index.html`` or ``README.md``.
        The default is ``None``, which displays all files in the directory.
    :arg boolean index: If ``true``, shows a directory index. If ``false``,
        raises a HTTP 404 error when users try to access a directory.
    :arg string index_template: The file to be used as the template for
        displaying the index. It can use 2 variables: ``$title`` and ``$body``.
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

    .. _glob pattern: https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob

    FileHandler exposes the following ``pathlib.Path`` attributes:

    ``root``
        Root path for this handler. Same as the ``path`` argument
    ``path``
        Absolute Path requested by the user, without adding a default filename
    ``file``
        Absolute Path served to the user, after adding a default filename
    '''

    SUPPORTED_METHODS = ("GET", "HEAD")

    def initialize(self, path, default_filename=None, index=None,
                   index_template=None, headers={}, transform={}, **kwargs):
        self.params = kwargs
        if isinstance(path, list):
            self.root = [Path(path_item).absolute() for path_item in path]
        else:
            self.root = Path(path).absolute()
        self.default_filename = default_filename
        self.index = index
        if index_template is not None:
            with Path(index_template).open(encoding='utf-8') as handle:
                self.index_template = string.Template(handle.read())
        else:
            self.index_template = dir_template
        self.headers = headers
        self.transform = {}
        for pattern, trans in transform.items():
            self.transform[pattern] = {
                'function': build_transform(trans, vars={'content': None, 'handler': None}),
                'headers': trans.get('headers', {}),
                'encoding': trans.get('encoding'),
            }

    def head(self, path=None):
        return self.get(path, include_body=False)

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self, path=None, include_body=True):
        self.include_body = include_body
        if isinstance(self.root, list):
            for path_item in self.root:
                yield self._get_path(path_item)
        elif path is None:
            yield self._get_path(self.root)
        else:
            # If the file doesn't exist, raise a 404: Not Found
            try:
                target = (self.root / path).resolve()
            except OSError:
                raise HTTPError(status_code=404)
            # If the file is not under root, raise a 403: Forbidden
            try:
                target.relative_to(self.root)
            except ValueError:
                raise HTTPError(status_code=403)
            yield self._get_path(target)

    @tornado.gen.coroutine
    def _get_path(self, path):
        self.path = path

        if self.path.is_dir():
            self.file = self.path / self.default_filename if self.default_filename else self.path
            if not (self.default_filename and self.file.exists()) and not self.index:
                raise HTTPError(status_code=404)
            # Ensure URL has a trailing '/' when displaying the index / default file
            if not self.request.path.endswith('/'):
                self.redirect(self.request.path + '/', permanent=True)
                return
        else:
            self.file = self.path
            if not self.file.is_file():
                raise HTTPError(
                    status_code=403,
                    log_message='%s is not a file or directory' % self.path)

        if self.path.is_dir() and self.index and not (
                self.default_filename and self.file.exists()):
            self.set_header('Content-Type', 'text/html')
            content = []
            for path in self.path.iterdir():
                # On Windows, pathlib on Python 2.7 won't handle Unicode. Ignore such files.
                # https://bitbucket.org/pitrou/pathlib/issues/25
                try:
                    content.append(u'<li><a href="{name!s:s}">{name!s:s}{dir!s:s}</a></li>'.format(
                        name=path.relative_to(self.path),
                        dir='/' if path.is_dir() else ''))
                except UnicodeDecodeError:
                    logging.warn("FileHandler can't show unicode file {:s}".format(
                        repr(path)))
            content.append(u'</ul>')
            self.content = self.index_template.substitute(title=self.path, body=''.join(content))

        else:
            modified = self.file.stat().st_mtime
            self.set_header('Last-Modified', datetime.datetime.utcfromtimestamp(modified))

            mime_type = mimetypes.types_map.get(self.file.suffix)
            if mime_type is not None:
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

                    output = []
                    for item in transform['function'](handler=self, content=self.content):
                        if tornado.concurrent.is_future(item):
                            item = yield item
                        output.append(item)
                    self.content = ''.join(output)
                self.set_header('Content-Length', len(utf8(self.content)))

        if self.include_body:
            self.write(self.content)
            self.flush()
