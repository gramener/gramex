from __future__ import unicode_literals

import string
import datetime
import mimetypes
import tornado.web
import tornado.gen
from pathlib import Path, PureWindowsPath
from fnmatch import fnmatch
from six import string_types
from tornado.escape import utf8
from tornado.web import HTTPError
from orderedattrdict import AttrDict
from six.moves.urllib.parse import urljoin
from .basehandler import BaseHandler
from gramex.config import objectpath, app_log
from gramex import conf as gramex_conf
from gramex.http import FORBIDDEN, NOT_FOUND

# Directory indices are served using this template by default
_default_index_template = Path(__file__).absolute().parent / 'filehandler.template.html'


def _match(path, pat):
    '''
    Check if path matches pattern -- case insensitively.
    '''
    # pathlib.match() does not accept ** -- it splits by path.
    # Use fnmatch if ** is present in the pattern.
    if '**' in pat:
        return fnmatch(str(path).lower(), '*/' + pat.lower())
    # Use PureWindowsPath to match case-insensitively
    return PureWindowsPath(path).match(pat)


def read_template(path):
    if not path.exists():
        app_log.warning('Missing directory template "%s". Using "%s"' %
                        (path, _default_index_template))
        path = _default_index_template
    with path.open(encoding='utf-8') as handle:
        return string.Template(handle.read())


class FileHandler(BaseHandler):
    '''
    Serves files with transformations. It accepts these parameters:

    :arg string path: Can be one of these:

        - The filename to serve. For all files matching the pattern, this
          filename is returned.
        - The root directory from which files are served. The first parameter of
          the URL pattern is the file path under this directory. Relative paths
          are specified from where gramex was run.
        - A wildcard path where `*` is replaced by the URL pattern's first
          `(..)` group.
        - A list of files to serve. These files are concatenated and served one
          after the other.

    :arg string default_filename: If the URL maps to a directory, this filename
        is displayed by default. For example, ``index.html`` or ``README.md``.
        The default is ``None``, which displays all files in the directory.
    :arg boolean index: If ``true``, shows a directory index. If ``false``,
        raises a HTTP 404: Not Found error when users try to access a directory.
    :arg list ignore: List of glob patterns to ignore. Even if the path matches
        these, the files will not be served.
    :arg list allow: List of glob patterns to allow. This overrides the ignore
        patterns, so use with care.
    :arg list methods: List of HTTP methods to allow. Defaults to
        `['GET', 'HEAD', 'POST']`.
    :arg string index_template: The file to be used as the template for
        displaying the index. If this file is missing, it defaults to Gramex's
        default ``filehandler.template.html``. It can use these string
        variables:

        - ``$path`` - the directory name
        - ``$body`` - an unordered list with all filenames as links
    :arg string template: Indicates that the contents of files matching this
        string pattern must be treated as a Tornado template. This is the same as
        specifying a ``function: template`` with the template string as a
        pattern. (new in Gramex 1.14).
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

    @classmethod
    def setup(cls, path, default_filename=None, index=None, index_template=None,
              template=None, headers={}, methods=['GET', 'HEAD', 'POST'], **kwargs):
        # Convert template: '*.html' into transform: {'*.html': {function: template}}
        # Do this before BaseHandler setup so that it can invoke the transforms required
        if template is not None:
            if template is True:
                template = '*'
            kwargs.setdefault('transform', AttrDict())[template] = AttrDict(function='template')
        super(FileHandler, cls).setup(**kwargs)

        cls.root, cls.pattern = None, None
        if isinstance(path, list):
            cls.root = [Path(path_item).absolute() for path_item in path]
        elif '*' in path:
            cls.pattern = path
        else:
            cls.root = Path(path).absolute()
        cls.default_filename = default_filename
        cls.index = index
        cls.ignore = cls.set(cls.kwargs.ignore)
        cls.allow = cls.set(cls.kwargs.allow)
        cls.index_template = read_template(
            Path(index_template) if index_template is not None else _default_index_template)
        cls.headers = AttrDict(objectpath(gramex_conf, 'handlers.FileHandler.headers', {}))
        cls.headers.update(headers)
        # Set supported methods
        for method in (methods if isinstance(methods, (tuple, list)) else [methods]):
            method = method.lower()
            setattr(cls, method, cls._head if method == 'head' else cls._get)

    @classmethod
    def set(cls, value):
        '''
        Convert value to a set. If value is already a list, set, tuple, return as is.
        Ensure that the values are non-empty strings.
        '''
        result = set(value) if isinstance(value, (list, tuple, set)) else set([value])
        for pattern in result:
            if not pattern:
                app_log.warning('%s: Ignoring empty pattern "%r"', cls.name, pattern)
            elif not isinstance(pattern, string_types):
                app_log.warning('%s: pattern "%r" is not a string. Ignoring.', cls.name, pattern)
            result.add(pattern)
        return result

    @tornado.gen.coroutine
    def _head(self, path=None):
        yield self._get(path, include_body=False)

    @tornado.gen.coroutine
    def _get(self, path=None, include_body=True):
        self.include_body = include_body
        if isinstance(self.root, list):
            # Concatenate multiple files and serve them one after another
            for path_item in self.root:
                yield self._get_path(path_item, multipart=True)
        elif path is None:
            # No group has been specified in the pattern. So just serve root
            yield self._get_path(self.root)
        else:
            # Eliminate parent directory references like `../` in the URL
            path = urljoin('/', path)[1:]
            if self.pattern:
                yield self._get_path(Path(self.pattern.replace('*', path)).absolute())
            else:
                yield self._get_path(self.root / path if self.root.is_dir() else self.root)

    def allowed(self, path):
        '''
        A path is allowed if it matches any allow:, or matches no ignore:.
        Override this method for a custom implementation.
        '''
        for ignore in self.ignore:
            if _match(path, ignore):
                # Check allows only if an ignore: is matched.
                # If any allow: is matched, allow it
                for allow in self.allow:
                    if _match(path, allow):
                        return True
                app_log.debug('%s: Disallow "%s". It matches "%s"', self.name, path, ignore)
                return False
        return True

    @tornado.gen.coroutine
    def _get_path(self, path, multipart=False):
        # If the file doesn't exist, raise a 404: Not Found
        try:
            path = path.resolve()
        except OSError:
            raise HTTPError(status_code=NOT_FOUND)

        self.path = path
        if self.path.is_dir():
            self.file = self.path / self.default_filename if self.default_filename else self.path
            if not (self.default_filename and self.file.exists()) and not self.index:
                raise HTTPError(status_code=NOT_FOUND)
            # Ensure URL has a trailing '/' when displaying the index / default file
            if not self.request.path.endswith('/'):
                self.redirect(self.request.path + '/', permanent=True)
                return
        else:
            self.file = self.path
            if not self.file.exists():
                raise HTTPError(status_code=NOT_FOUND)
            elif not self.file.is_file():
                raise HTTPError(status_code=FORBIDDEN, log_message='%s is not a file' % self.path)

        if not self.allowed(self.file):
            raise HTTPError(status_code=FORBIDDEN)

        if self.path.is_dir() and self.index and not (
                self.default_filename and self.file.exists()):
            self.set_header('Content-Type', 'text/html; charset=UTF-8')
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
                    app_log.warning("FileHandler can't show unicode file {!r:s}".format(path))
            content.append(u'</ul>')
            self.content = self.index_template.substitute(path=self.path, body=''.join(content))

        else:
            modified = self.file.stat().st_mtime
            self.set_header('Last-Modified', datetime.datetime.utcfromtimestamp(modified))

            mime_type = mimetypes.types_map.get(self.file.suffix)
            if mime_type is not None:
                if mime_type.startswith('text/'):
                    mime_type += '; charset=UTF-8'
                self.set_header('Content-Type', mime_type)

            for header_name, header_value in self.headers.items():
                if isinstance(header_value, dict):
                    if _match(self.file, header_name):
                        for header_name, header_value in header_value.items():
                            self.set_header(header_name, header_value)
                else:
                    self.set_header(header_name, header_value)

            transform = {}
            for pattern, trans in self.transform.items():
                if _match(self.file, pattern):
                    transform = trans
                    break

            encoding = transform.get('encoding')
            with self.file.open('rb' if encoding is None else 'r', encoding=encoding) as file:
                self.content = file.read()
                if transform:
                    for header_name, header_value in transform['headers'].items():
                        self.set_header(header_name, header_value)

                    output = []
                    for item in transform['function'](content=self.content, handler=self):
                        if tornado.concurrent.is_future(item):
                            item = yield item
                        output.append(item)
                    self.content = ''.join(output)
                self.set_header('Content-Length', len(utf8(self.content)))

        if self.include_body:
            self.write(self.content)
            # Do not flush unless it's multipart. Flushing disables Etag
            if multipart:
                self.flush()
