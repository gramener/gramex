Server
======

The server is the core engine of Gramex. It offers services such as URL
mapping, logging, caching, etc that applications use.

Gramex expects a ``gramex.yaml`` in the directory where it is run from. This
overrides Gramex's own default ``gramex.yaml`` configuration. You can import
other config files and over-ride further.

Here's a simple ``gramex.yaml`` that serves the file ``index.html`` as the home
page::

    url:                        # URL configuration section
      root:                     # Add a configuration called "root"
        pattern: /              # It maps the URL / (the home page)...
        handler: FileHandler    # ... to a Gramex FileHandler
        kwargs:                 # ... and passes it these arguments:
          path: index.html      # Use index.html as the path to serve

Imports
~~~~~~~

One config file can import another. For example::

    import:
      app1: 'app1/gramex.yaml'        # import this YAML file (relative path)
      app2: 'd:/temp/gramex.yaml'     # import this YAML file (absolute path)
      subapps: '*/gramex.yaml'        # import gramex.yaml in any subdirectory
      deepapps: '**/gramex.yaml'      # import gramex.yaml from any subtree

The keys ``app1``, ``app2``, etc. are just identifiers, not used for anything.
The values must be YAML files. These are loaded in order. After loading, the
``import:`` section is removed.

If a file is missing, Gramex proceeds with a warning.

UNIX shell style wildcards work. ``*`` matches anything, and ``**`` matches all
subdirectories.

Imports work recursively. You can have imports within imports.


Variables
~~~~~~~~~

Variables are written as ``{VARIABLE}``. By default, all environment variables
are available. For example::

    import:
      home_config: {HOME}/gramex.yaml   # imports gramex.yaml from your home directory

You can define or override variables using the ``variables:`` section::

    variables:
      URLROOT: "/site"                  # Define {URLROOT}
      HOME: {default: "/home"}          # Define {HOME} if not defined earlier


Services
--------

The YAML files are grouped into one section per service:

::

    version: 1.0    # Gramex and API version
    app: ...        # Main app configuration section
    url: ...        # URL mapping section
    log: ...        # Logging configuration
    schedule: ...   # Scheduled tasks config
    watch: ...      # Watch files for changes
    mime: ...       # Custom mime type definitions
    email: ...      # Email configuration
    ...             # etc. -- one section per service

Here is the full ``gramex.yaml`` specification.

.. literalinclude:: ../gramex/gramex.yaml
   :language: yaml
   :linenos:

Notes
~~~~~

- Configurations are pure YAML, and do not have any tags.
- Configurations are loaded as ordered `AttrDict`_ files and stored in the
  variable ``gramex.conf``. If the underlying YAML files change, then
  ``gramex.init()`` is automatically reloaded and all services are re-
  initialized.
