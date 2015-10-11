.. :changelog:

History
-------

1.0.2 (2015-10-11)
~~~~~~~~~~~~~~~~~~

* Implement :ref:`FunctionHandler` that renders any function
* :ref:`DirectoryHandler` transforms files (e.g. converting
  Markdown or YAML to HTML)
* :ref:`gramex.transforms.badgerfish` transform converts YAML to HTML
* When a configuration file is changed, it is reloaded immediately
* Document Gramex at https://learn.gramener.com/gramex/
* Add test cases for handlers

1.0.1 (2015-09-09)
~~~~~~~~~~~~~~~~~~

* Is a directory-browsing webserver (:class:`gramex.handlers.DirectoryHandler`)
* Works with Python 3 in addition to Python 2
* Add test cases with full coverage for :mod:`gramex.config` and
  :mod:`gramex.confutil`
* Logs display friendly dates, and absolute paths instead of relative paths

1.0.0 (2015-09-08)
~~~~~~~~~~~~~~~~~~

* First release of core server
