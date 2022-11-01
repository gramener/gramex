import os
import re
import string
import datetime
import mimetypes
import tornado.web
import tornado.gen
import gramex.cache
from pathlib import Path
from fnmatch import fnmatch
from tornado.escape import utf8
from tornado.web import HTTPError
from collections import defaultdict
from orderedattrdict import AttrDict
from urllib.parse import urljoin, urlsplit, urlunsplit
from .basehandler import BaseHandler
from gramex.config import objectpath, app_log
from gramex import conf as gramex_conf
from gramex.http import FORBIDDEN, NOT_FOUND

# Directory indices are served using this template by default
_folder = os.path.dirname(os.path.abspath(__file__))
_default_index_template = os.path.join(_folder, 'filehandler.template.html')
_tmpl_opener = gramex.cache.opener(string.Template, read=True, encoding='utf-8')


def _match(path, pat):
    '''
    Check if path matches pattern -- case insensitively.
    '''
    return fnmatch(str(path).lower(), '*/' + pat.lower())


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
        - A dict of {regex: path}. If the URL matches the regex, the path is
          served. The path is string formatted using the regex capture groups

    :arg string default_filename: If the URL maps to a directory, this filename
        is displayed by default. For example, ``index.html`` or ``README.md``.
        It can be a list of default filenames tried in order, e.g.
        ``[index.template.html, index.html, README.md]``.
        The default is ``None``, which displays all files in the directory
        using the ``index_template`` option.
    :arg boolean index: If ``true``, shows a directory index. If ``false``,
        raises a HTTP 404: Not Found error when users try to access a directory.
    :arg list ignore: List of glob patterns to ignore. Even if the path matches
        these, the files will not be served.
    :arg list allow: List of glob patterns to allow. This overrides the ignore
        patterns, so use with care.
    :arg string index_template: The file to be used as the template for
        displaying the index. If this file is missing, it defaults to Gramex's
        default ``filehandler.template.html``. It can use these string
        variables:

        - ``$path`` - the directory name
        - ``$body`` - an unordered list with all filenames as links
    :arg dict headers: HTTP headers to set on the response.
    :arg dict transform: Transformations that should be applied to the files.
        The key matches one or more `glob patterns`_ separated by space/comma
        (e.g. ``'*.md, 'data/**'``.) The value is a dict with the same
        structure as :class:`FunctionHandler`, and accepts these keys:

        ``function``
            The expression to return. Example: ``function: mymodule.transform(content, handler)``.
            ``content`` has the file contents. ``handler`` has the FileHandler object

        ``encoding``
            The encoding to read the file with, e.g. ``utf-8``. If ``None`` (the default), the
            file is read as bytes, and the transform `function` MUST accept the content as bytes

        ``headers``:
            HTTP headers to set on the response
    :arg string template: ``template="*.html"`` renders all HTML files as Tornado templates.
        ``template=True`` renders all files as Tornado templates (new in Gramex 1.14).
    :arg string sass: ``sass="*.sass"`` renders all SASS files as CSS (new in Gramex 1.66).
    :arg string scss: ``scss="*.scss"`` renders all SCSS files as CSS (new in Gramex 1.66).
    :arg string ts: ``ts="*.ts"`` renders all TypeScript files as JS (new in Gramex 1.78).

    .. _glob patterns: https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob

    FileHandler exposes these attributes:

    - ``root``: Root path for this handler. Aligns with the ``path`` argument
    - ``path``; Absolute path requested by the user, without adding a default filename
    - ``file``: Absolute path served to the user, after adding a default filename
    '''

    @classmethod
    def setup(
        cls,
        path,
        default_filename=None,
        index=None,
        index_template=None,
        headers={},
        default={},
        **kwargs,
    ):
        # Convert template: '*.html' into transform: {'*.html': {function: template}}
        # Convert sass: ['*.scss', '*.sass'] into transform: {'*.scss': {function: sass}}
        # Do this before BaseHandler setup so that it can invoke the transforms required
        for key in ('template', 'sass', 'scss', 'ts', 'vue'):
            val = kwargs.pop(key, None)
            if val:
                # template/sass/...: true is the same as template: '*'
                val = '*' if val is True else val if isinstance(val, (list, tuple)) else [val]
                kwargs.setdefault('transform', AttrDict()).update(
                    {v: AttrDict(function=key) for v in val}
                )
        super(FileHandler, cls).setup(**kwargs)

        cls.root, cls.pattern = None, None
        if isinstance(path, dict):
            cls.root = AttrDict([(re.compile(p + '$'), val) for p, val in path.items()])
        elif isinstance(path, list):
            cls.root = [Path(path_item).absolute() for path_item in path]
        elif '*' in path:
            cls.pattern = path
        else:
            cls.root = Path(path).absolute()
        # Convert default_filename into a list
        if not default_filename:
            cls.default_filename = []
        elif isinstance(default_filename, list):
            cls.default_filename = default_filename
        else:
            cls.default_filename = [default_filename]
        cls.index = index
        cls.ignore = cls.set(cls.kwargs.ignore)
        cls.allow = cls.set(cls.kwargs.allow)
        cls.default = default
        cls.index_template = index_template or _default_index_template
        cls.headers = AttrDict(objectpath(gramex_conf, 'handlers.FileHandler.headers', {}))
        cls.headers.update(headers)
        cls.post = cls.put = cls.delete = cls.patch = cls.get
        if not kwargs.get('cors'):
            cls.options = cls.get

    @classmethod
    def set(cls, value):
        '''
        Convert value to a set. If value is already a list, set, tuple, return as is.
        Ensure that the values are non-empty strings.
        '''
        result = set(value) if isinstance(value, (list, tuple, set)) else {value}
        for pattern in result:
            if not pattern:
                app_log.warning(f'{cls.name}: Ignoring empty pattern "{pattern!r}"')
            elif not isinstance(pattern, (str, bytes)):
                app_log.warning(f'{cls.name}: pattern "{pattern!r}" is not a string. Ignoring.')
            result.add(pattern)
        return result

    @tornado.gen.coroutine
    def head(self, *args, **kwargs):
        kwargs['include_body'] = False
        yield self.get(*args, **kwargs)

    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        self.include_body = kwargs.pop('include_body', True)
        path = urljoin('/', args[0] if len(args) else '').lstrip('/')
        if isinstance(self.root, list):
            # Concatenate multiple files and serve them one after another
            for path_item in self.root:
                yield self._get_path(path_item, multipart=True)
        elif isinstance(self.root, dict):
            # Render path for the the first matching regex
            for pattern, filestr in self.root.items():
                match = pattern.match(path)
                if match:
                    q = defaultdict(str, **self.default)
                    q.update({k: v[0] for k, v in self.args.items() if len(v) > 0})
                    q.update(match.groupdict())
                    p = Path(filestr.format(*match.groups(), **q)).absolute()
                    app_log.debug(f'{self.name}: {self.request.path} renders {p}')
                    yield self._get_path(p)
                    break
            else:
                raise HTTPError(NOT_FOUND, f'{self.request.path} matches no path key')
        elif not args:
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
                app_log.debug(f'{self.name}: Disallow "{path}". It matches "{ignore}"')
                return False
        return True

    @tornado.gen.coroutine
    def _get_path(self, path, multipart=False):
        # If the file doesn't exist, raise a 404: Not Found
        try:
            path = path.resolve()
        except OSError:
            raise HTTPError(NOT_FOUND, f'{path} missing')

        self.path = path
        if self.path.is_dir():
            self.file = self.path
            for default_filename in self.default_filename:
                self.file = self.path / default_filename
                if self.file.exists():
                    break
            if not (self.default_filename and self.file.exists()) and not self.index:
                raise HTTPError(NOT_FOUND, f'{self.file} missing index')
            # Ensure URL has a trailing '/' when displaying the index / default file
            if not self.request.path.endswith('/'):
                p = urlsplit(self.xrequest_uri)
                r = urlunsplit((p.scheme, p.netloc, p.path + '/', p.query, p.fragment))
                self.redirect(r, permanent=True)
                return
        else:
            self.file = self.path
            if not self.file.exists():
                raise HTTPError(NOT_FOUND, f'{self.file} missing')
            elif not self.file.is_file():
                raise HTTPError(FORBIDDEN, f'{self.path} is not a file')

        if not self.allowed(self.file):
            raise HTTPError(FORBIDDEN, f'{self.file} not allowed')

        # Display the list of files for directories without a default file
        if (
            self.path.is_dir()
            and self.index
            and not (self.default_filename and self.file.exists())
        ):
            self.set_header('Content-Type', 'text/html; charset=UTF-8')
            content = []
            file_template = string.Template('<li><a href="$path">$name</a></li>')
            for path in self.path.iterdir():
                if path.is_symlink():
                    name_suffix, path_suffix = ' &#x25ba;', ''
                elif path.is_dir():
                    name_suffix = path_suffix = '/'
                else:
                    name_suffix = path_suffix = ''
                path = str(path.relative_to(self.path))
                content.append(
                    file_template.substitute(
                        path=path + path_suffix,
                        name=path + name_suffix,
                    )
                )
            content.append('</ul>')
            try:
                tmpl = gramex.cache.open(self.index_template, _tmpl_opener)
            except OSError:
                app_log.exception(f'{self.name}: index_template: {self.index_template} failed')
                tmpl = gramex.cache.open(_default_index_template, _tmpl_opener)
            self.content = tmpl.substitute(path=self.path, body=''.join(content))

        else:
            modified = self.file.stat().st_mtime
            self.set_header('Last-Modified', datetime.datetime.utcfromtimestamp(modified))

            mime_type = mimetypes.types_map.get(self.file.suffix.lower())
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

            # Use the first matching transform.
            transform = {}
            for pattern, trans in self.transform.items():
                # Patterns may be specified as '*.md, *.MD, md/**' -- split by comma or space
                if any(_match(self.file, part) for part in pattern.replace(',', ' ').split()):
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
