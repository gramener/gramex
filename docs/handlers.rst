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

See :class:`gramex.handlers.FunctionHandler` for details.


.. _FileHandler:

FileHandler
~~~~~~~~~~~

(In version 1.0.3 and before, this was called ``DirectoryHandler``. Both work.)

Displays files in a folder. This configuration serves files from the current
directory at ``/``::

    url:
      root-app:                         # A unique name for this handler
        pattern: /(.*)                  # All URLs beginning with /
        handler: gramex.handlers.FileHandler        # Handler used
        kwargs:                                     # Options to the handler
            path: .                                 #   path is current dir
            default_filename: index.html            #   default filename

See :class:`gramex.handlers.FileHandler` for details.

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

