Gramex
======

Gramex is a declarative data analytics and visualization platform.

Installation
------------

.. _git: https://git-scm.com/
.. _Anaconda: http://continuum.io/downloads

Gramex is distributed via ``pip``. Install `git`_ and `Anaconda`_. Then::

    # Install via SSH
    pip install git+ssh://git@code.gramener.com/s.anand/gramex.git@master

    # ... or install via HTTP (and type your username + password)
    pip install git+http://code.gramener.com/s.anand/gramex.git@master

The ``@master`` branch has the latest stable version. For the latest development
version, use ``@dev`` instead of ``@master``.

To upgrade an existing installation, run ``pip install --upgrade`` instead of
``pip install``.

Usage
-----

Run Gramex::

    gramex

Gramex runs at ``http://127.0.0.1:8888/`` and will show the current directory by
default.


Design
------

Gramex 1.0 is a backward-incompatible re-boot of the visualisation
platform.

-  *Why 1.0* We use semantic versioning. ``1.0`` means we have a
   published API that we follow.
-  *Why backward-incompatible* There are many bad practices that Gramex
   0.x encourages that we want to break-away from. For example,
   inconsistent attributes in chart components.

This is the work-in-progress design.

Principles
----------

These are the core principles of Gramex.

1. **Data, not code** Apps are written my changing configurations. Code
   is a last resort.
2. **YAML** for configurations, not XML (verbose), or JSON (no
   commenting). No extensions -- only standard YAML.
3. **Automated reloads**. Configurations are reloaded transparently.
4. **Modular**. Nearly every part is a module, usable independently.
5. **Modular licensing**. It can be broken down into smaller parts that
   can be licensed independently, with customisable trials.
6. **Web rendering**. All views are rendered via HTML/CSS/JS, not Python.

These are proposed principles, for discussion.

1. **User-friendly** at every stage. Move from code to data. From data
   to GUI. From GUI to live editing.
2. **Lazy computations**. Defer computation to as late as possible.
3. **RESTful**. Use REST APIs and friendly URLs.

Architecture
------------

Gramex has:

-  **A core server**, which provides a variety of services (via Python
   libraries) to the entire application.
-  **Libraries** for apps to use. Like Python, there is one (and
   preferably only one) obvious library for a task.
-  **Handlers**, which handle specific URL patterns as required. They
   may show templates, act as a websocket, provide a data interface,
   serve static files, etc.
-  **Components**, which can be used by handlers to render certain kinds
   of outputs.

Server
------

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

Configurations are pure YAML, and do not have any tags. The YAML files
are grouped into one section per service:

::

    version: 1.0    # Gramex and API version
    app: ...        # Main app configuration section
    url: ...        # URL mapping section
    log: ...        # Logging configuration
    cache: ...      # Caching configuration
    email: ...      # Email configuration
    ...             # etc. -- one section per service

Here is the YAML specification.

.. literalinclude:: ../gramex/gramex.yaml
   :language: yaml
   :linenos:

Note that these services are **NOT** provided by Gramex:

-  **Distributed computing** is handled by the apps themselves. This can
   be via an external computing engine (e.g. Spark) or one that is
   custom-built.
-  **Load balancing** is handled by a front-end balancer (e.g. nginx).

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
---------

Gramex uses and recommends the following libraries:

- cryptography: `cryptography <https://cryptography.io/>`__
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

Handlers
--------

A handler converts a HTTP request into a response. (It is an instance of Tornado
`RequestHandler`_.)

.. _RequestHandler: http://tornado.readthedocs.org/en/latest/web.html#request-handlers

Some default handlers are provided by Gramex, and this can be extended by users.

DirectoryHandler
~~~~~~~~~~~~~~~~

Displays files in a folder.

YAMLHandler
~~~~~~~~~~~

Converts YAML to HTML via the `badgerfish`_ convention and renders the response.

References:

- badgerfish: http://www.sklar.com/badgerfish/
- XML and JSON conventions: http://wiki.open311.org/JSON_and_XML_Conversion/
- Yahoo convention: https://developer.yahoo.com/javascript/json.html#xml
- xmlconv: https://github.com/chbrown/xmlconv/tree/master/lib

TemplateHandler
~~~~~~~~~~~~~~~

Renders a Tornado template


Other handlers
~~~~~~~~~~~~~~

We are considering these handlers.

- **Middleware handlers** that add decorater methods on other handlers
- **Namespaced app folders**.
  - Reserved namespaces
  - Add a directory ``app/``, and the URL mappings for ``/app/...``
    will be taken from the ``app/`` directory.
  - With ``/app/`` there is full flexibility on how to handle the URLs
  - No URLs outside ``/app/`` will be affected.
  - Configurations use data, not code. (e.g. YAML, not Python)
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
- **AJAX support** for templates
- **Websockets**


Components
----------

**Browsers supported** are IE11, Edge, Chrome, Firefox, mobile Safari. From Jan
12 2016, `IE10 won't be supported`_.

.. _IE10 won't be supported: https://support.microsoft.com/en-us/gp/microsoft-internet-explorer

`Web components`_ allow custom HTML elements. With a small `polyfill`_, target
browsers are supported.

.. _Web components: http://webcomponents.org/
.. _polyfill: https://github.com/WebComponents/webcomponentsjs



Layered data-driven approach

- Composable components. Apply a component over another in a way
- Scaling and other transformations
- Axes
- Default stroke colour, stroke width, padding, etc
- Attribute lambda parameters
- Transformable. Transforms should also be composable.
- Ability to access template intermediate variables (layouts, scales,
  etc) from outside on server and client side
- Themes
- Any symbol instead of default symbols

Flexible rendering:

- Rendering may be on the client side or the server side
- Rendered views can be edited on the client side as well
- Renderable for PPTX, PDF, PNG, SVG, etc
- Responsive on the server side (re-layout) or the client side
  (preserve aspect)
- CSS classes reserved for components

Containers and controls:

- Grids
- Themes
- Standard components

Interactive charts:

- Animated transitions
- Cross-filter like filtering
- How will we incorporate dynamic interactive controls?
- Interactivity involves 3 things (We don't have a catalogue of any of
  these):
    1. Events / components (brushing, clicking, sliding, etc)
    2. Actions (filter, zoom-in, etc)
    3. Combinations (click-to-filter, etc)

Intelligence:

-  Automated colour contrast
-  Automated placement of legends
-  Automated placement of labels
-  Automated placement of annotations
-  Text wrapping and fitting

Support

-  IPython Notebooks

Others
------

-  Sample datasets
-  App store for apps and data

Thoughts
--------

-  How will be incorporate PowerPoint Smart-Art-like infographic
   layouts?
-  Can we make these infographics without any coding? Bret Victor like?
-  Concepts:

   -  Layouts (pack in a shape, grow from a point, stack in a grid)
   -  Renderings (shape, photo, size/color/other attributes)
   -  Narratives

-  How will we incorporate autolysis?
-  Voice / video rendering
-  Async Gramex References:
-  `Ben Darnell's template plans for Tornado
   4.1 <https://groups.google.com/forum/?fromgroups#!searchin/python-tornado/template$20asynchronous%7Csort:date/python-tornado/Eoyb2wphJ-o/fj9EAb166PIJ>`__
-  ```asynchronous`` directive pull
   request <https://github.com/tornadoweb/tornado/pull/553>`__
-  ```coroutine=`` parameter pull
   request <https://github.com/tornadoweb/tornado/pull/1311>`__
-  Interesting libraries:
-  `Vega <http://vega.github.io/>`__
-  ggvis.rstudio.com
-  Watch OpenVisConf videos:
   https://www.youtube.com/user/BocoupLLC/videos
-  Packaging via
   `cookiecutter <https://github.com/audreyr/cookiecutter>`__

Discussion notes
----------------

-  **Will we have multiple instances of Gramex sharing the same
   memory?** No. This is difficult to implement in Python. Intsead, it
   will be delegated to external engines (databases, Spark, etc.)
-  **Will we shift to PyPy?** No. Most libraries (such as database
   drivers, lxml, etc.) do not yet work on PyPy.

Project plan
------------

**Bold dates** indicate milestones. *Italic dates* indicate plans.
Normal dates indicate actual activity.

- **Mon 31 Aug**: Begin Gramex 1.0
- Mon 31 Aug: Define Gramex config syntax, logging and scheduling
  services
- Tue 1 Sep: Define config layering, error handling, component
  requirements
- Wed 2 Sep: Build prototype. Explore component approach. Share project
  plan
- Thu 3 Sep: Add config, scehduler and logger services. Explore
  component approach
- Fri 4 Sep: Core server ready for release.
- **Fri 4 Sep**: Core server spec and prototype release
- Mon 7 Sep: Explore Vega, dask
- Tue 8 Sep: Add DirectoryHandler, 1.0.0 release
- Wed 9 Sep: Update documentation
- **Mon 14 Sep**: Handler and component spec
- *Mon 14 Sep*: Anand: create a HTML - YAML interconverter handler. This will be
  the primary templating handler we will use
- Mon 14 Sep: Explore web components
- Tue 15 Sep: Create an XML - data interconversion engine
- *Tue 15 Sep*: Pratap: create ``<vega-chart>`` and ``<vega-lite>`` webcomponents
- *Wed 16 Sep*: Anand: create a Node.js handler in Tornado
- *Thu 17 Sep*: Pratap: create examples of most charts on learn.gramener.com
  using ``<vega-lite>`` or ``<vega-chart>``
- *Fri 18 Sep*: Document handler and component spec. Write client collateral on
  technology stack direction: Tornado, Blaze, node, Vega, Web components
- **Mon 21 Sep**: Revised handler and component spec and prototype.
  Components listed
- **Mon 26 Oct**: Spec freeze. Components early release.
- **Mon 9 Nov**: Gramex 1.0 beta release to testing. Start bugfixing
- **Mon 23 Nov**: Gramex 1.0 release
