.. :changelog:

History
-------

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
* ``FileHandler`` supports an ``index_template:`` key that allows customised
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
* ``FileHandler`` accepts multiple ``path``s as an array. The output of these
  files are concatenated after transformated.
* In the ``FileHandler`` config, you can use ``pattern: /abc`` instead of
  ``pattern: /(abc)`` if you are mapping a single URL to a single path.
* ``FileHandler`` supports ``function: template`` in the transforms section.
  This treats the file as a tornado template and renders the output.
* ``FileHandler`` directory listing looks prettier now.
* ``DataHandler`` supports ``like`` and ``notlike`` operations.
* The ``watch:`` section of ``gramex.yaml`` allows you to trigger events when
  files are changed.


1.0.4 (2016-03-30)
~~~~~~~~~~~~~~~~~~

* ``FunctionHandler`` supports co-routines and works asynchronously
* ``FileHandler`` is the new name for ``DirectoryHandler`` (both will work)
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
