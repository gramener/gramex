.. :changelog:

History
-------

1.14 (2016-08-11)
~~~~~~~~~~~~~~~~~

- `TwitterStream`_ is a scheduler function that provides Twitter Streaming API
  support.
- `FacebookGraphHandler`_ lets you use the Facebook data via the Graph API.
- `QueryHandler`_ lets you execute arbitrary SQL queries with parameters.
- `DataHandler`_ accepts a ``?count=1`` parameter and returns an ``X-Count``
  HTTP header that has the number of rows in the query (ignoring limit/offset).
- All handlers support an ``xsrf_cookies: false`` to disable XSRF cookies for a
  specific handler.
- Add a ``template: "*.html"`` to `FileHandler`_ kwargs to render all HTML files
  as Tornado templates. ``template: true`` renders all files as templates.


1.13 (2016-08-01)
~~~~~~~~~~~~~~~~~

- All handlers support custom `error handlers`_. You can show custom 404, 500
  pages.
- `SimpleAuth`_ is an extremely simple login handler you can use for testing
- `ProcessHandler`_ supports the ``redirect:`` config (used by many handlers)
  to redirect the user after the process is executed.
- `DataHandler`_ supports a ``thread: false``. This switches to a synchronous
  version that is (currently) less buggy.
- Variables can be assigned different values in different environments via a
  simple `conditional variables`_ syntax.

1.12 (2016-07-21)
~~~~~~~~~~~~~~~~~

* `DBAuth`_ features a forgot password feature.
* `FileHandler`_ supports ``POST`` and other HTTP methods via the ``methods:``
  configuration. ``POST`` is now available by default.
* The ``cache:`` key supports user attributes. You can cache responses based on
  the user.
* Gramex loads a bit faster by importing slow modules (e.g. Pandas) only if
  required.

1.11 (2016-07-15)
~~~~~~~~~~~~~~~~~

* A data browser app is ready. Run ``gramex install databrowser`` and then
  ``gramex run databrowser`` to run it at any time.
* `UploadHandler`_ allows users to upload and manage files.
* `TwitterRESTHandler`_ allows end-users to log in and use their own access.
  tokens. It can also limit the API to just a single method.
* By default, `TwitterAuth`_ redirects users back to the same URL that initiated
  the login request.
* The `email`_ service allows developers to send emails via SMTP services (e.g.
  GMail, Yahoo, etc.)
* ``gramex setup`` can be run in any directory to run the `apps`_ setup. It runs
  ``setup.sh``, ``setup.py``, ``Makefile``, ``npm install``, ``bower install``,
  etc.
* If an app has ``requirements.txt``, the `apps`_ setup also runs ``pip install
  -r requirements.txt``.
* The ``template:`` config is now optional for `LDAPAuth`_ and `DBAuth`_. A
  built-in (but minimal) login screen is available by default.
* The ``redirect:`` config (used by many handlers) supports relative URLs.
* Gramex's log no longer shows the user name on the console by default. This was
  making the request logs quite long.

1.10 (2016-07-01)
~~~~~~~~~~~~~~~~~

* `DataHandler`_ can now write back into relational databases. This lets you
  create form-based applications easily.
* `DataHandler`_ displays only the first 100 rows by default. (It used to
  display the entire table, which was slow.)
* `DataHandler`_ caches metadata (i.e. table column names) until restarted or
  until ``gramex.yaml`` changes. This speeds up DataHandler considerably.
* `TwitterRESTHandler`_ lets you access the Twitter API easily without blocking
  the server.
* You can add ``set_xsrf: true`` to the ``kwargs:`` of any URL handler. This
  sets the XSRF cookie when the URL is loaded.
* If ``gramex.yaml`` has duplicate keys, Gramex raises an error, warning you
  up-front.
* The ``handlers.BaseHandler.log.format`` config lets you define the application
  log format. The default value is
  ``'%(status)d %(method)s %(uri)s (%(ip)s) %(duration).1fms %(user)s'``. It can
  be overridden to use any other format.


1.0.9 (2016-06-15)
~~~~~~~~~~~~~~~~~~

* Gramex supports `sessions`_. Whether a user is logged in or not,
  ``handler.session`` is a persistent dictionary that you can use to store
  information against that user session.
* Users can log in via LDAP and ActiveDirectory using the `LDAPAuth`_ handler.
* Users can log in via any database table containing user IDs and passwords
  using the `DBAuth`_ handler.
* All auth handlers support a consistent `auth redirection`_, allowing apps to
  redirect them to the right page after login.
* Users can log out via the `LogoutHandler`_.
* User login is logged via `auth logging`_ to a CSV file.
* When a user logs in, you can perform custom actions (such as logging them out
  of other sessions)
* All URLs support `authorization`_ via an `auth:` section. You can check if the
  user is member of a group, or any arbitrary condition defined as a Python
  function.
* `FileHandler`_ allows you to `ignore files`_ matching a pattern.
* Gramex automatically logs startup and shutdown events using the ``eventlog:``
  service. It checks the `Gramex update page`_ daily for updates, and uploads
  the event log.
* A new ``none`` pre-defined `log`_ handler is available. It ignores log events.
* ``gramex update <app>`` re-installs the app.
* Press ``Ctrl+B`` on the console to start the browser (in case you forgot
  ``--browser``.)

1.0.8 (2016-06-01)
~~~~~~~~~~~~~~~~~~

* Gramex supports installation of `apps`_. You can run ``gramex install <app>
  <url>`` to install an app from a folder, git repo, URL, etc. Apps can define
  setup scripts (such as bower install, etc.) which will be executed after the
  app is installed. ``gramex uninstall <app>`` uninstalls the app
* Apps are run via ``gramex run <app>``. Local apps are run via ``gramex run
  <app> --target=DIR``. Any command line options (e.g. ``--listen.port=8888`` or
  ``--browser=true``) will be stored and re-used with the next ``gramex run
  <app>``.
* The new `debug`_ module has two timer methods ``gramex.debug.timer`` and
  ``gramex.debug.Timer``, and a line profiler decorator
  ``gramex.debug.lineprofile``. These will help profile your functions.
* Press ``Ctrl+D`` on the Gramex console to start the interactive IPython
  debugger. This freezes Gramex and lets you run commands inside Gramex.
* Run ``gramex --debug.exception=true`` to start the debugger when any handler
  encounters an exception.
* `FileHandler`_ supports pattern mapping. This makes it easier to flexibly map
  URL patterns to filenames.
* ``gramex.yaml`` can use two new variables: ``$GRAMEXPATH`` -- the path where
  Gramex is installed, and ``$GRAMEXDATA`` -- the path where Gramex apps are
  installed by default.
* You can override values after an ``import:`` in ``gramex.yaml``.
* Console logs are now in colour on all platforms.
* ``Ctrl+C`` will shutdown Gramex gracefully. You no longer need ``Ctrl+Break``.

There are two changes that may disrupt your code:

* If you have invalid functions in ``gramex.yaml``, Gramex will no longer run.
  Remove or fix them.
* Files served by Gramex's ``default`` FileHandler are cached on the browser for
  1 minute. Press ``Ctrl+F5`` to reload. Override the ``default`` FileHandler to
  change this behaviour.


1.0.7 (2016-05-15)
~~~~~~~~~~~~~~~~~~

* We have a new `JSONHandler`_ that implements a JSON store. It is similar to
  the `Firebase API`_. It lets you save, modify and retrieve any JSON structure.
  It is intended for small data (typically under 1MB) like settings.
* All handlers support `caching`_. Any request can be cached for a fixed
  duration. The cache can be in-memory or disk-based (shareable across
  instances) and both caches have a size limit imposed. The cache key can also
  be configured.
* The `scheduler`_ supports threads. Using the ``thread: true`` configuration
  runs the scheduled task in a separate thread.
* The `log`_ section now supports 2 additional handlers (apart from ``console``).
    * ``access-log`` writes information logs to a CSV file ``access.csv``
    * ``warn-log`` writes warnings to a CSV file ``warn.csv``
* A new ``threadpool:`` service has been added. This is used internally by
  services to run code in a separate thread. You can use ``threapool.workers``
  to specify the number of concurrent threads that are allowed.
* Gramex handlers are now passed a ``name`` and ``conf`` parameter which
  identifies the name and configuration used to create them.
* The ``AuthHandler`` falls back to weaker HTTPS certificate verification --
  specifically if Google authentication fails due to older HTTPS certificates on
  systems.


1.0.6 (2016-05-01)
~~~~~~~~~~~~~~~~~~

* In the ``app:`` section, the ``browser:`` key accepts either ``true`` or any
  URL. If a URL is provided, it opens the browser at that URL on startup. If
  ``true``, it opens the browser to the home page of the application.
* Gramex config variables (in the ``variables:`` section) may contain other
  variables. For example, you can define a variable ``HOME`` in a
  ``config.yaml``. This can be re-used in the variables section of an imported
  YAML file as ``$HOME``.
* Config variables can be computed using the ``function:`` parameter. For
  example, ``VAR: {function: module.fn}`` will run ``module.fn()`` and assign
  ``$VAR`` the returned value.
* `FileHandler`_ supports an ``index_template:`` key that allows customised
  directory listings. It can be any custom-styled HTML file that uses ``$path``
  and ``$body`` respectively to represent the full path to the directory and the
  contents of the directory.
* ``DataHandler`` is now asynchronous. Requests won't be blocked while queries run.
* ``ProcessHandler`` accepts ``stdout`` and ``stderr`` parameters. These can be
  ``false`` to ignore the output, or set to any file name (to save the output /
  errors in that file.) The default for ``stdout`` and ``stderr`` is ``pipe``,
  which sends the output to the browser.
* Gramex defers loading of services to ensure a faster initial loading time.
* Gramex guide is a part of Gramex. There's no need to install it separately.


1.0.5 (2016-04-15)
~~~~~~~~~~~~~~~~~~

* Gramex config YAML files support custom variables. You can define a variable
  in the ``variables:`` section and use it as ``$VARIABLE`` anywhere in the YAML
  file, its imports or in subsequent layers. They default to environment
  variables.
* You can use the pre-defined variables ``$YAMLFILE`` (current YAML file name),
  ``$YAMLPATH`` (current YAML directory), and ``$YAMLURL`` (relative URL path
  from where Gramex is running to current YAML directory) in your template.
* Command line arguments override the ``app:`` configuration. So running
  ``gramex --listen.port=8999`` from the command line will run Gramex on port
  8999, irrespective of the port configuration.
* Add a ``browser: true`` to automatically start the browser on Gramex launch.
  You can also use ``gramex --browser=true``.
* ``ProcessHandler`` implemented. It runs any program as a sub-process and
  streams the output to the request.
* ``FunctionHandler`` accepts co-routines for asynchronous processing. Functions
  can also ``yield`` strings that will be immediately written and flushed,
  providing a streaming interface.
* `FileHandler`_ accepts multiple ``path`` as an array. The output of these
  files are concatenated after transformated.
* In the `FileHandler`_ config, you can use ``pattern: /abc`` instead of
  ``pattern: /(abc)`` if you are mapping a single URL to a single path.
* `FileHandler`_ supports ``function: template`` in the transforms section.
  This treats the file as a tornado template and renders the output.
* `FileHandler`_ directory listing looks prettier now.
* ``DataHandler`` supports ``like`` and ``notlike`` operations.
* The ``watch:`` section of ``gramex.yaml`` allows you to trigger events when
  files are changed.


1.0.4 (2016-03-30)
~~~~~~~~~~~~~~~~~~

* ``FunctionHandler`` supports co-routines and works asynchronously
* `FileHandler`_ is the new name for ``DirectoryHandler`` (both will work)
* Implement authentication via Google, Twitter and Facebook OAuth
* Simpler installation steps


1.0.3 (2016-01-18)
~~~~~~~~~~~~~~~~~~

* Implement ``DataHandler`` that displays data from databases (via
  `SQLAlchemy <http://www.sqlalchemy.org/>`__ and `Blaze <http://blaze.pydata.org/>`__)
* ``DirectoryHandler``:
    - lets gramex.yaml specify input file encoding (defaults to UTF-8)
    - takes both content as well as the handler as input
* gramex.yaml URL priority can be specified explicitly using ``priority:``

1.0.2 (2015-10-11)
~~~~~~~~~~~~~~~~~~

* Implement ``FunctionHandler`` that renders any function
* ``DirectoryHandler`` transforms files (e.g. converting Markdown or YAML to
  HTML)
* ``gramex.transforms.badgerfish`` transform converts YAML to HTML
* When a configuration file is changed, it is reloaded immediately
* Document Gramex at https://learn.gramener.com/gramex/
* Add test cases for handlers

1.0.1 (2015-09-09)
~~~~~~~~~~~~~~~~~~

* Is a directory-browsing webserver (``gramex.handlers.DirectoryHandler``)
* Works with Python 3 in addition to Python 2
* Add test cases with full coverage for ``gramex.config`` and
  ``gramex.confutil``
* Logs display friendly dates, and absolute paths instead of relative paths

1.0.0 (2015-09-08)
~~~~~~~~~~~~~~~~~~

* First release of core server


.. _Firebase API: https://www.firebase.com/docs/rest/api/
.. _JSONHandler: https://learn.gramener.com/guide/jsonhandler/
.. _FileHandler: https://learn.gramener.com/guide/filehandler/
.. _DataHandler: https://learn.gramener.com/guide/datahandler/
.. _QueryHandler: https://learn.gramener.com/guide/queryhandler/
.. _TwitterRESTHandler: https://learn.gramener.com/guide/twitterresthandler/
.. _FacebookGraphHandler: https://learn.gramener.com/guide/facebookgraphhandler/
.. _LogoutHandler: https://learn.gramener.com/guide/auth/#log-out
.. _LDAPAuth: https://learn.gramener.com/guide/auth/#ldap
.. _DBAuth: https://learn.gramener.com/guide/auth/#simple-auth
.. _DBAuth: https://learn.gramener.com/guide/auth/#database-auth
.. _TwitterAuth: https://learn.gramener.com/guide/auth/#twitter-auth
.. _TwitterStream: https://learn.gramener.com/guide/twitterresthandler/#twitter-streaming
.. _UploadHandler: https://learn.gramener.com/guide/auth/uploadhandler/
.. _caching: https://learn.gramener.com/guide/cache/
.. _scheduler: https://learn.gramener.com/guide/scheduler/
.. _log: https://learn.gramener.com/guide/config/#logging
.. _apps: https://learn.gramener.com/guide/apps/
.. _debug: https://learn.gramener.com/guide/debug/
.. _sessions: https://learn.gramener.com/guide/auth/#sessions
.. _login actions: https://learn.gramener.com/guide/auth/#login-actions
.. _auth logging: https://learn.gramener.com/guide/auth/#logging
.. _authorization: https://learn.gramener.com/guide/auth/#authorization
.. _Gramex update page: https://gramener.com/gramex-update/
.. _ignore files: https://learn.gramener.com/guide/filehandler/#ignore-files
.. _auth redirection: https://learn.gramener.com/guide/auth/#redirection
.. _email: https://learn.gramener.com/guide/email/
.. _conditional variables: https://learn.gramener.com/guide/config/#conditional-variables
.. _error handlers: https://learn.gramener.com/guide/config/#error-handlers
