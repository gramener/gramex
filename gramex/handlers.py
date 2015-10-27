import re
import yaml
import datetime
import mimetypes
import pandas as pd
from pathlib import Path
from orderedattrdict import AttrDict
from .transforms import build_transform
from tornado.web import HTTPError, RequestHandler
from sqlalchemy import create_engine, MetaData, select, asc, desc, and_


class FunctionHandler(RequestHandler):
    '''
    Renders the output of a function. It accepts these parameters when
    initialized:

    :arg string function: a string that resolves into any Python function or
        method (e.g. ``str.lower``). By default, it is called as
        ``function(handler)`` where handler is this RequestHandler, but you can
        override ``args`` and ``kwargs`` below to replace it with other
        parameters. The result is rendered as-is (and hence must be a string.)
        If ``redirect`` is specified, the result is discarded and the user is
        redirected to ``redirect``.
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
              function: str                             # Display string as-is
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
    def initialize(self, **kwargs):
        self.function = build_transform(kwargs, vars='handler')
        self.headers = kwargs.get('headers', {})
        self.redirect_url = kwargs.get('redirect', None)

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
            ``handler`` and ``content`` are replaced with the RequestHandler and
            file contents respectively.

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
                content.append(u'<li><a href="{name!s:s}">{name!s:s}{dir!s:s}</a></li>'.format(
                    name=path.relative_to(self.path),
                    dir='/' if path.is_dir() else ''))
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
                self.set_header('Content-Length', len(self.content))

        if include_body:
            self.write(self.content)


drivers = {}


class DataHandler(RequestHandler):
    '''
    Serves data in specified format from datasource. It accepts these parameters:

    :arg dict kwargs: keyword arguments to be passed to the function.
    :arg string url: The path at which datasource (db, csv) is located.
    :arg string driver: Connector to be used to connect to datasource
        Like -(sqlalchemy, pandas.read_csv). Currently supports sqlalchemy.
    :arg dict parameters: Additional keyword arguments for driver.
    :arg dict headers: HTTP headers to set on the response.
        Currently supports csv, json, html table

    Here's a simple use -- to return a csv file as a response to a URL. This
    configuration renders `flags` table in t`utorial.db` database as `file.csv`
    at the URL `/datastore/flags`::

        url:
            flags:
                pattern: /datastore/flags               # Any URL starting with /datastore/flags
                handler: datastore.DataHandler          # uses DataHandler
                kwargs:
                    driver: sqlalchemy                  # Using sqlalchemy driver
                    url: sqlite:///C:/path/tutorial.db  # Connects to database at this path/url
                    table: flags                        # to this table
                    parameters: {encoding: utf8}        # with additional parameters provided
                    headers:
                        Content-Type: text/csv          # and served as csv, ('application/json', 'text/html')

    '''
    def initialize(self, **kwargs):
        self.params = kwargs

    def get(self):
        args = AttrDict(self.params)
        if args.driver != 'sqlalchemy':
            raise NotImplementedError('Only driver=sqlalchemy is supported')

        key = yaml.dump(args)
        if key not in drivers:
            parameters = args.get('parameters', {})
            drivers[key] = create_engine(self.params['url'], **parameters)
        self.driver = drivers[key]

        qargs = self.request.arguments
        meta = MetaData(bind=self.driver, reflect=True)
        table = meta.tables[self.params['table']]

        if qargs.get('_select'):
            query = select([table.c[c] for c in qargs.get('_select')])
        else:
            query = select([table])

        if qargs.get('_where'):
            wh_re = re.compile(r'(\w+)([=><|&~!]{1,2})(\w+)')
            wheres = []
            for where in qargs.get('_where'):
                match = wh_re.search(where)
                if match is None:
                    continue
                col, oper, val = match.groups()
                col = table.c[col]
                if oper == '==':
                    wheres.append(col == val)
                elif oper == '!':
                    wheres.append(col != val)
                elif oper == '~':
                    wheres.append(col.ilike('%' + val + '%'))
                elif oper == '!~':
                    wheres.append(col.notlike('%' + val + '%'))
                elif oper == '>=':
                    wheres.append(col >= val)
                elif oper == '<=':
                    wheres.append(col <= val)
                elif oper == '>':
                    wheres.append(col > val)
                elif oper == '<':
                    wheres.append(col < val)
            query = query.where(and_(*wheres))

        if qargs.get('_sort'):
            order = {'asc': asc, 'desc': desc}
            sorts = []
            for sort in qargs.get('_sort'):
                odr, col = sort.split(':', 1)
                sorts.append(order.get(odr, asc)(col))
            query = query.order_by(*sorts)

        if qargs.get('_offset'):
            query = query.offset(qargs.get('_offset')[0])
        if qargs.get('_limit'):
            query = query.limit(qargs.get('_limit')[0])

        self.result = pd.read_sql_query(query, self.driver)

        for header_name, header_value in self.params['headers'].items():
            self.set_header(header_name, header_value)

        if self.params['headers']['Content-Type'] == 'application/json':
            self.content = self.result.to_json(orient='records')
        if self.params['headers']['Content-Type'] == 'text/html':
            self.content = self.result.to_html()
        if self.params['headers']['Content-Type'] == 'text/csv':
            self.content = self.result.to_csv(index=False)
            self.set_header("Content-Disposition", "attachment;filename=file.csv")

        self.write(self.content)
        self.flush()
