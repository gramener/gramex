Handlers
--------

A handler converts a HTTP request into a response. (It is an instance of Tornado
`RequestHandler`_.)

.. _RequestHandler: http://tornado.readthedocs.org/en/latest/web.html#request-handlers

Gramex provides the following built-in handlers.


.. _FunctionHandler:

FunctionHandler
~~~~~~~~~~~~~~~

Runs a function and displays the output. For example, this configuration
displays "Hello world" at /hello as plain text::

    url:
      hello-world:
        pattern: /hello                     # The URL /hello
        handler: FunctionHandler            # Runs a function
        kwargs:
          function: six.text_type           # Convert to string
          args:                             # with these arguments:
            - Hello world                   # just one "Hello world"
          headers:
            Content-Type: text/plain        # Render as plain text

You can call a function that you have defined. For example, create a
``calculations.py`` with this method::

    import json
    def total(*items):
        'Calculate total of all items and render as JSON: value and string'
        total = sum(float(item) for item in items)
        return json.dumps({
            'display': '${:,.2f}'.format(total),
            'value': total,
        })

Now, you can use this configuration::

    url:
      total:
        pattern: /total                             # The URL /total
        handler: FunctionHandler                    # Runs a function
        kwargs:
          function: calculations.total              # calculations.total(100, 200.0)
          args: [100, 200.0]
          headers:
            Content-Type: application/json          # Returns the result as JSON

... to get this result in JSON::

    {"display": "$300.00", "value": 300.0}

URL patterns
::::::::::::

You can specify wildcards in the URL pattern. For example::

    url:
      lookup:
        pattern: /name/([a-z]+)/age/([0-9]+)        # e.g. /name/john/age/21
        handler: FunctionHandler                    # Runs a function
        kwargs:
          function: calculations.name_age           # Run this function

When you access ``/name/john/age/21``, ``john`` and ``21`` can be accessed
via ``handler.path_args`` as follows::

    def name_age(handler):
        name = handler.path_args[0]
        age = handler.path_args[1]

Function arguments
::::::::::::::::::

``args`` has the arguments passed to the function. If no ``args`` is
specified, the Tornado `RequestHandler`_ is passed as the only positional
argument. For example, in ``calculations.py``, add::

    def add(handler):
        return str(sum(float(x) for x in handler.get_arguments('x')))

Now, the following configuration::

    function: calculations.add

... takes the URL ``?x=1&x=2&x=3`` to add up 1, 2, 3 and display ``6.0``.

You can pass the handler along with custom arguments. ``=handler`` is
replaced by the RequestHandler. For example::

    url:
      method:
        pattern: /method          # The URL /method
        handler: FunctionHandler  # Runs a function
        kwargs:
          function: calculations.method
          args:
              - =handler          # This is replaced with the RequestHandler
              - 10
          kwargs:
              h: =handler         # This is replaced with the RequestHandler
              val: 0

... calls ``calculations.method(handler, 10, h=handler, val=0)``.


Asynchronous functions
::::::::::::::::::::::

You can use asynchronous functions via Tornado's `Coroutines`_ like this::

    @tornado.gen.coroutine
    def fetch(url1, url2):
        client = tornado.httpclient.AsyncHTTPClient()
        r1, r2 = yield [client.fetch(url1), client.fetch(url2)]
        raise tornado.gen.Return(r1.body + r2.body)

This ``fetch`` function can be used as a FunctionHandler.

The simplest way to call a blocking function asynchronously is to use a
``ThreadPoolExecutor``::

    thread_pool = concurrent.futures.ThreadPoolExecutor(4)

    @tornado.gen.coroutine
    def calculate(data1, data2):
        group1, group2 = yield [
            thread_pool.submit(data1.groupby, ['category']),
            thread_pool.submit(data2.groupby, ['category']),
        ]
        result = thead_pool.submit(pd.concat, [group1, group2])
        raise tornado.gen.Return(result)

.. _Coroutines: http://tornado.readthedocs.org/en/stable/guide/coroutines.html

Redirection
:::::::::::

To redirect to a different URL when the function is done, use ``redirect``::

    url:
      lookup:
        function: calculation.run     # Run calculation.run(handler)
        redirect: /                   # and redirect to / thereafter

Use ``redirect: ""`` to redirect to the URL  redirects to referrer. Add test case for this.


See :class:`gramex.handlers.FunctionHandler` for details.


.. _FileHandler:

FileHandler
~~~~~~~~~~~

Displays files in a folder. This configuration serves files from the current
directory at ``/``::

    url:
      root-app:                         # A unique name for this handler
        pattern: /(.*)                  # All URLs beginning with /
        handler: FileHandler            # Handler used
        kwargs:                                 # Options to the handler
            path: .                             #   path is current dir
            default_filename: index.html        #   default filename
            index: true                         # List files if index.html doesn't exist

**Note**: Gramex comes with a ``default`` URL handler that automatically serves
files from the home directory of your folder. To override that, override the
``default`` pattern::

    url:
      default:                          # This overrides the default URL handler
        pattern: ...


Redirection
:::::::::::

To serve a specific file a URL, i.e. effectively offering URL redirection,
specify the appropriate pattern and path. For example, if you have a
``data.csv``, you can serve it at ``/data`` as follows::

    pattern: /data
    handler: FileHandler
    kwargs:
      path: data.csv

The URL will be served with the MIME type of the file. CSV files have a MIME
type ``text/csv`` and a ``Content-Disposition`` set to download the file. You
can override these headers::

    pattern: /data
    handler: FileHandler
    kwargs:
      path: data.csv
      headers:
        Content-Type: text/plain
        Content-Disposition: none


File patterns
:::::::::::::

To restrict to serving specific files, you can identify them in the pattern::

    pattern: /blog/(.*\.md$|style\.css)         # Serve only .md files or style.css
    handler: FileHandler
    kwargs:
      path: blog/

Transforms
::::::::::

To render Markdown as HTML, set up this handler::

    pattern: /blog/(.*)                     # Any URL starting with blog
    handler: FileHandler                    # uses this handler
    kwargs:
      path: blog/                           # Serve files from blog/
      default_filename: README.md           # using README.md as default
      transform:
        "*.md":                             # Any file matching .md
          encoding: cp1252                  #   Open files with CP1252 encoding
          function: markdown.markdown       #   Convert from markdown to html
          kwargs:
            safe_mode: escape               #   Pass safe_mode='escape'
            output_format: html5            #   Output in HTML5
          headers:
            Content-Type: text/html         #   MIME type: text/html

.. _glob pattern: https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob
.. _SimpleHTTPServer: https://docs.python.org/2/library/simplehttpserver.html


See :class:`gramex.handlers.FileHandler` for details.

.. _BadgerFish: http://www.sklar.com/badgerfish/



DataHandler
~~~~~~~~~~~

TBD.

Similar to `Webstore <http://webstore.readthedocs.org/en/latest/index.html>`__

See :class:`gramex.handlers.DataHandler` for details.


Writing your own handlers
~~~~~~~~~~~~~~~~~~~~~~~~~

You an write your own handler by extending `RequestHandler`_. For example,
create a file called ``hello.py`` with the following content::

    from tornado.web import RequestHandler

    class Hello(RequestHandler):
        def get(self):
            self.write('hello world')

Now, you can use ``handler: hello.Hello`` to send the response ``hello world``.


Upcoming handlers
~~~~~~~~~~~~~~~~~

We are considering writing handlers for these:

- **Auth**
    - Authentication mechanism (OAuth, SAML, LDAP, etc.)
    - Admin: User - role mapping and expiry management
    - Apps expose a ``function(user, roles, request)`` to the server
      that determines the rejection, type of rejection, error message,
      log message, etc.
    - Apps can internally further limit access based on role (e.g. only
      admins can see all rows.)
    - An app can be an auth provider. By default, a ``/admin/`` app can
      provide uer management functionality
- **Uploads**
- **Websockets**
