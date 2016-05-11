from __future__ import unicode_literals

import string
import logging
import datetime
import mimetypes
import tornado.web
import tornado.gen
from pathlib import Path
from tornado.escape import utf8
from tornado.web import HTTPError
from six.moves.urllib.parse import urljoin
from .basehandler import BaseHandler
from ..transforms import build_transform


# Directory indices are served using this template by default
_default_index_template = Path(__file__).absolute().parent / 'filehandler.template.html'


def read_template(path):
    if not path.exists():
        logging.warn('Missing directory template "%s". Using "%s"' %
                     (path, _default_index_template))
        path = _default_index_template
    with path.open(encoding='utf-8') as handle:
        return string.Template(handle.read())


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
        displaying the index. If this file is missing, it defaults to Gramex's
        default ``filehandler.template.html``. It can use these string
        variables:

        - ``$path`` - the directory name
        - ``$body`` - an unordered list with all filenames as links

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
        if isinstance(path, list):
            self.root = [Path(path_item).absolute() for path_item in path]
        else:
            self.root = Path(path).absolute()
        self.default_filename = default_filename
        self.index = index
        self.index_template = read_template(
            Path(index_template) if index_template is not None else _default_index_template)
        self.headers = headers
        self.transform = {}
        for pattern, trans in transform.items():
            self.transform[pattern] = {
                'function': build_transform(trans, vars={'content': None, 'handler': None}),
                'headers': trans.get('headers', {}),
                'encoding': trans.get('encoding'),
            }
        super(FileHandler, self).initialize(**kwargs)

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
            # Collapse all the ../ etc in the URL
            path = urljoin('/', path)[1:]
            yield self._get_path(self.root / path if self.root.is_dir() else self.root)

    @tornado.gen.coroutine
    def _get_path(self, path):
        # If the file doesn't exist, raise a 404: Not Found
        try:
            path = path.resolve()
        except OSError:
            raise HTTPError(status_code=404)

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
            if not self.file.exists():
                raise HTTPError(status_code=404)
            elif not self.file.is_file():
                raise HTTPError(status_code=403, log_message='%s is not a file' % self.path)

        if self.path.is_dir() and self.index and not (
                self.default_filename and self.file.exists()):
            self.set_header('Content-Type', 'text/html')
            content = []
            file_template = string.Template(u'<li><a href="$path">$name</a></li>')
            for path in self.path.iterdir():
                if path.is_symlink():
                    name_suffix, path_suffix = ' &#x25ba;', ''
                elif path.is_dir():
                    name_suffix = path_suffix = '/'
                else:
                    name_suffix = path_suffix = ''
                # On Windows, pathlib on Python 2.7 won't handle Unicode. Ignore such files.
                # https://bitbucket.org/pitrou/pathlib/issues/25
                try:
                    path = str(path.relative_to(self.path))
                    content.append(file_template.substitute(
                        path=path + path_suffix,
                        name=path + name_suffix,
                    ))
                except UnicodeDecodeError:
                    logging.warn("FileHandler can't show unicode file {!r:s}".format(path))
            content.append(u'</ul>')
            self.content = self.index_template.substitute(path=self.path, body=''.join(content))

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
