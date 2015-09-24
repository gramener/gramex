Server
======

The server is the core engine of Gramex. It offers services such as URL
mapping, logging, caching, etc that applications use.

The server is configured by layered config files. The server has a
default ``gramex.yaml``. Gramex runs in a home directory, which can have
a ``gramex.yaml``, and can define other config files that further
over-ride it.

Configurations are loaded as ordered `AttrDict`_ files and stored in the
variable ``gramex.config``. Apps can update this and run
``gramex.reconfigure()`` to update all configurations (except ``app:`` and
``conf:``).

.. _AttrDict: https://github.com/mk-fg/layered-yaml-attrdict-config

Configurations are pure YAML, and do not have any tags.

Services
--------

The YAML files are grouped into one section per service:

::

    version: 1.0    # Gramex and API version
    app: ...        # Main app configuration section
    url: ...        # URL mapping section
    log: ...        # Logging configuration
    cache: ...      # Caching configuration
    email: ...      # Email configuration
    ...             # etc. -- one section per service

Here is the full ``gramex.yaml`` specification.

.. literalinclude:: ../gramex/gramex.yaml
   :language: yaml
   :linenos:

Note that these services are **NOT** provided by Gramex:

-  **Distributed computing** is handled by the apps themselves. This can
   be via an external computing engine (e.g. Spark) or one that is
   custom-built.
-  **Load balancing** is handled by a front-end balancer (e.g. nginx).

These **WILL** be provided by Gramex, but are not available yet.

The server provides an admin view that allows admins to see (and modify)
the configurations. (It does not show the history or source of the
setting, though.)

The server is asynchronous. It executes on an event loop that
applications can use (for deferred execution, for example). The server
also runs a separate thread that can:

-  Interrupt long requests, even without the consent of the app. (For
   example, if the connection closes, just stop the function.)
-  Re-load changed config files into memory
-  Deferred logging
-  etc.

However, all request handlers will run on a single thread, since Tornado
RequestHandler is not thread-safe.


Libraries
~~~~~~~~~

Gramex uses and recommends the following libraries:

- cryptography: `cryptography <https://cryptography.io/>`__
- file watching: `watchdog <http://pythonhosted.org/watchdog/>`__
- ETL: `odo <http://odo.readthedocs.org/en/latest/>`__,
  `dask <http://dask.readthedocs.org/en/latest/>`__ and
  `blaze <http://blaze.pydata.org/en/latest/>`__

These are candidates:

- fake data:
  `fake-factory <https://pypi.python.org/pypi/fake-factory>`__
- slugs:
  `awesome-slugify <https://pypi.python.org/pypi/awesome-slugify>`__
  with
  `unslug <https://github.com/sanand0/awesome-slugify/tree/unslug>`__
- NLP: Cannot use `spaCy <http://spacy.io/>`__ due to license
- machine learning: [scikit-learn] + [theano]
- email
