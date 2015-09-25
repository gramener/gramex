Handlers
--------

A handler converts a HTTP request into a response. (It is an instance of Tornado
`RequestHandler`_.)

.. _RequestHandler: http://tornado.readthedocs.org/en/latest/web.html#request-handlers

Gramex provides these handlers. (See :mod:`gramex.handlers` for full
documentation.)


.. _FunctionHandler:

FunctionHandler
~~~~~~~~~~~~~~~

Runs a function and displays the output. For example, this configuration
displays "Hello world" at /hello as plain text::

    url:
      hello-world:
        pattern: /hello                     # The URL /hello
        handler: gramex.handlers.FunctionHandler   # Runs a function
        kwargs:
          function: six.text_type           # Convert to string
          args:                             # with these arguments:
            - Hello world                   # just one "Hello world"
          headers:
            Content-Type: text/plain        # Render as plain text

For more details on creating functions and passing arguments, see
:func:`gramex.transforms.build_transform`.

To redirect to a different URL when the function is done, use ``redirect``::

    url:
      calculation:
        pattern: /calc                      # The URL /calc
        handler: gramex.handlers.FunctionHandler   # Runs a function
        kwargs:
          function: module.calculation      # module.calculation()
          redirect: /                       # and redirects to / thereafter


.. _DirectoryHandler:

DirectoryHandler
~~~~~~~~~~~~~~~~

Displays files in a folder. This configuration serves files from the current
directory at ``/``::

    url:
      root-app:                         # A unique name for this handler
        pattern: /(.*)                  # All URLs beginning with /
        handler: gramex.handlers.DirectoryHandler   # Handler used
        kwargs:                                     # Options to the handler
            path: .                                 #   path is current dir
            default_filename: index.html            #   default filename


.. _TransformHandler:

TransformHandler
~~~~~~~~~~~~~~~~

Converts the configuration into other formats such as HTML using transformation
functions.

For example, to create a static blog that serves Markdown files as HTML, use::

    url:                                  # Add a URL configuration
      blog-app:                           # named blog-app.
        pattern: /blog/(.*)               # The /blog/ URL uses TransformHandler
        handler: gramex.handlers.TransformHandler
        kwargs:                           # with these arguments:
          path: D:/blog/                  # Serve files from this folder
          default_filename: index.md      # Directory index file
          transform:
            "*.md":                           # Convert .md to HTML via Markdown
              function: markdown.markdown     # Run markdown.markdown(file)
              headers:
                "Content-Type": text/html     # Response is served as text/html

The ``function:`` can be any Python function that a string input and returns a
string output. :func:`gramex.transforms.build_transform` explains how to
configure Python functions as transforms.

You can specify different transformations for different file patterns. For
example, to serve YAML files as HTML via :func:`gramex.transform.badgerfish`::

    url:                                  # Add a URL configuration
      blog-app:                           # named blog-app.
        pattern: /blog/(.*)               # The /blog/ URL uses TransformHandler
        handler: gramex.handlers.TransformHandler
        kwargs:                           # with these arguments:
          path: .                         # Serve files from this folder
          default_filename: index.yaml    # Directory index file
          transform:
            "*.yaml":                     # Convert .yaml to HTML via BadgerFish
              function: gramex.transforms.badgerfish
              kwargs:
                mapping:                      # badgerfish() allows tag transforms
                  vega-chart:                 # All <vega-chart> tag contents
                    function: json.dumps      # are rendered as JSON
              headers:
                "Content-Type": text/html
            "*.md":                           # Convert .md to HTML via Markdown
              function: markdown.markdown     # Run markdown.markdown(file)
              headers:
                "Content-Type": text/html     # Response is served as text/html

Any ``*.yaml`` file is transformed via :func:`gramex.transform.badgerfish` into
HTML via the `BadgerFish`_ convention before the response is rendered. Any
``*.md`` file is transformed via ``markdown.markdown`` into HTML.

.. _BadgerFish: http://www.sklar.com/badgerfish/


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

- **Data API**. Perhaps like
  `Webstore <http://webstore.readthedocs.org/en/latest/index.html>`__
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

