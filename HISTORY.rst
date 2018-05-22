.. :changelog:

History
-------

v1.35.0 (2018-05-21)
~~~~~~~~~~~~~~~~~~~~

See `v1.35 release notes`_

v1.34.0 (2018-05-02)
~~~~~~~~~~~~~~~~~~~~

See `v1.34 release notes`_

v1.33.0 (2018-04-15)
~~~~~~~~~~~~~~~~~~~~

See `v1.33 release notes`_

v1.32.0 (2018-04-01)
~~~~~~~~~~~~~~~~~~~~

See `v1.32 release notes`_

v1.31.0 (2018-03-15)
~~~~~~~~~~~~~~~~~~~~

See `v1.31 release notes`_


v1.30.0 (2018-02-28)
~~~~~~~~~~~~~~~~~~~~

See `v1.30 release notes`_


v1.29.0 (2018-02-15)
~~~~~~~~~~~~~~~~~~~~

`SAMLAuth`_ is now a part of Gramex. Most enterprise Single-Sign-On (SSO)
implementations are now SAML-enabled, including Microsoft ActiveDirectory.
Gramex can integrate with all of these apps now. (@vinay.ranjan)

`ProxyHandler`_ is a new handler that lets you:

1. Access data from server-side APIs directly from the browser
   (e.g. Gmail API, Google Translate, SalesForce API, etc)
2. Expose non-Gramex applications within a Gramex app -- using Gramex Auth.

`FormHandler`_ has several enhancements:

- `FormHandler tables`_ are a client-side component that quickly render FormHandler data as tables
- Using `FormHandler parameters`_ you can allow users to choose the file,
  database or table. This is using URL query parameters like ``?table=...`` as
  well as path arguments like ``/database/table``.
- You can specify HTTP headers for all formats using the ``headers:`` kwarg.
- `FormHandler headers`_ now has an example of CORS - accessing FormHandler data
  from other servers via HTTP (@pratap.vardhan)
- Examples of matrix and grid charts for `FormHandler charts`_ are available (@pratap.vardhan)

`Alerts command line`_ usage gives you access to `Smart alerts`_ give you access
to alert emails from command line. You can use this as a local mail merge app.

`FunctionHandler`_ supports the ``method:`` kwarg. You can decide which HTTP
methods to support - including ``PUT``, ``DELETE``, etc.

A few common queries are documented:

- `session data`_ features a guide on how to pick a session store --
  specifically, how to handle sessions with multiple Gramex instances (@pratam.vardhan)
- `How XSRF works`_ explains the underlying workings of XSRF

Stats:

- Code base: 21,636 lines (gramex: 13,772 - a reduction, tests: 7,864)
- Test coverage: 79%


v1.28.0 (2018-01-31)
~~~~~~~~~~~~~~~~~---

`FormHandler`_ has two major upgrades. `FormHandler charts`_ use the `Seaborn`_
library to generate static charts on the server as SVG or PNG (PDF too.) Setting
``?meta=y`` returns metadata as HTTP headers.

The `UI component library`_ now uses `Bootstrap 4`_ stable version. New components are:

- ``.modal-left`` and ``.modal-right`` overlays
- `numeral.js`_ library
- `g1`_ is upgraded to v0.4 which features an improved ``$().formhandler()``
  component. This lets you render FormHandler data as an interactive Excel-like
  table component. (@tejesh.papineni)

`Smart alerts`_ can now:

- fetch images and attachments from URLs. This lets you attach dashboards as
  PDFs or images in conjunction with `CaptureHandler`_
- specify an option to run the alert only once, based on any condition. This
  lets you stop repeated emails of the same kind
- define data in-place in the YAML, rather than using a file or a database
- log all alerts sent in a log file
- use the first ``email:`` service defined by default (you don't need to specify a ``service:`` every time)

`PPTXHandler`_ exposes URL query parameters in the configuration. This lets you
generate presentations whose content can be updated by the URL. For example, you
can create a certificate template, and set ``?name=`` to update the recipient's
name. (@ranjan.balappa).

`FunctionHandler`_ can now return NumPy objects as well -- not just Python objects. (@tejesh.papineni)

Thanks to the recent Docuthon, documentation has improved. Key changes:

- The `deploy`_ section features a checklist (@vinay.ranjan) and how to set up Gramex as a service
- The `UI component library`_ documents how to create equal height layouts (@mohmad.jakeer)
- Steps to create pre-defined Gramex `apps`_ are documented

Note: the ``condition()`` transform is deprecated. No known repository uses it.

Stats:

- Code base: 21,478 lines (gramex: 13,822, tests: 7,656)
- Test coverage: 79% (reduced due to new features with less test coverage)


v1.27.0 (2018-01-20)
~~~~~~~~~~~~~~~~~~~~
`g1`_ is upgraded to v0.3 which features a ``$().formhandler()`` component.
This renders FormHandlers as Excel-like tables (sortable, filterable).

`FormHandler`_ supports a ``?meta=y`` query parameter that returns metadata
about the query. This includes the number of rows, offset, limit, sort options,
columns excluded, etc.

The `UI component library`_ now uses `Bootstrap 4 Beta 3`_. New components are:

- ``.arrow-tail`` which adds a tail to arrows
- ``.border-radius-sm``, ``.border-radius-lg``, etc which create rounded corners of different sizes
- ``.btn-xs`` for extra-small buttons
- ``.modal-xl`` for extra-large modals
- ``.cursor-pointer`` as a utility class for ``cursor: pointer``
- Improvements to ``.switch`` and ``.upload``

The `UI component library`_ page itself is more usable:

- Theme fonts now include a few (carefully picked) Google Fonts
- The sidebar is sticky.
- The "Toggle source" button at the top lets you view / hide source code
- The list of libraries are better documented

`CaptureHandler`_ supports repeated ``?dpi=`` arguments for PPTX that allow
creating multiple slides with differently sized images  (@pragnya.reddy).
``?title_size=`` sets the title font size for pptx.

Using auth handlers for `AJAX login`_ is now well documented.

A new `session data`_ store type called ``type: sqlite`` is available. This
is a bit slower, but allows multiple Gramex instances to share session data.

`Smart Alerts`_ templates can now access the Gramex config. This lets you re-use
templates across different alerts, changing static content in the YAML
configuration (@mukul.taneja).

Gramex supports a `docker install`_ option. The documentation also features
common `Windows administration`_ options used when deploying Gramex.

Stats:

- Code base: 21,062 lines (gramex: 13,496, tests: 7,566)
- Test coverage: 81%


v1.26.0 (2017-12-31)
~~~~~~~~~~~~~~~~~~~~
This release features an upgrade to the `UI component library`_:

- `g1`_ is the new Gramex interaction library. It is bundled with Gramex and
  currently features URL manipulation, templating and a few utilities.
- `Leaflet`_, `topojson`_, `shepherd`_ and `select2`_ are built into Gramex.
- `Ripples`_ are available as a CSS utility class
- `Background`_ and `Gradient`_ utilities are available
- The Bootstrap theme at ``/ui/bootstraptheme.css`` is minified by default

`CaptureHandler`_ for Chrome supports a ``window.renderComplete`` option. Set
``?delay=renderComplete``. This waits until ``window.renderComplete`` is true
and then captures the page.

`DBAuth`_ can use a CSV file as its database.

`PPTXHandler`_ handles edge cases better:

- Custom text is allowed in heatgrid by @abhilash.maddireddy
- BulletChart handles NaNs / identical values - and other bugfixes by @pratap.vardhan

This release also adds better debugging features:

- ``gramex --settings.debug`` sets the console log level to DEBUG. This makes it
  easier to start Gramex in debug mode.
- `FormHandler`_ and :py:func:`gramex.debug.cache` print the executed query in debug mode
- The console logs now print the handler name that rendered the URL

Gramex now uses `bandit`_ to test for internal vulnerabilities like SQL injection.

Stats:

- Code base: 20,825 lines (gramex: 13,480, tests: 7,345)
- Test coverage: 80%


v1.25.0 (2017-12-15)
~~~~~~~~~~~~~~~~~~~~
This release features `Smart Alerts`_ - a rule-based email alert service. This
can be used to:

- Send customized reports on a schedule
- Send alerts only if specific events happen
- Mail different groups different reports based on their roles, only if required

The `UI component library`_ has been extended with several custom components:

- Hover, focus and active styles
- Text size classes
- Underline classes
- Absolute positioning classes
- Overlay classes
- Divider component
- Tail (callout) component
- Switches (styled checkboxes)

Also, D3 4.0 is now part of the UI components library.

A basic `Log viewer`_ app is part of Gramex. It shows the history of all pages
accessed on Gramex.

Gramex console logs are more informative. Each request prints the name of the
handler used to process it. This tells you whether the correct handler processed
the URL or not. Also, when starting up, the list of all handler classes and
priorities and shown.

To enable debug mode from the command prompt, run ``gramex --settings.debug``.

Credits:

- `Smart Alerts`_ by @mukul.taneja
- `UI component library`_ by @bhanu.kamapantula
- `Log viewer`_ by @fibinse

Stats:

- Code base: 20,832 lines (gramex: 13,500, tests: 7,332)
- Test coverage: 81%

v1.24.0 (2017-11-30)
~~~~~~~~~~~~~~~~~~~~
**Note**: Before installing this release, you install `node`_ 8.x or above, and
also run ``npm install -g yarn``. Also run ``pip install`` with a ``--verbose``
option. Gramex installs several UI libraries and the installation is slow. Yarn
speeds up the installation. ``--verbose`` lets you see progress.

This release adds a `UI component library`_ that includes a series of standard
front-end libraries and a Gramex-customized version of Bootstrap 4. By @bhanu.kamapantula

All auth handlers support a `inactive expiry`_ feature that closes a session if
no requests were made for a certain period.

`DBAuth`_ supports a `Sign up`_ feature that lets users create their own
accounts. By @nikhil.kabbin

`DBAuth`_ used to ignore the ``redirect:`` key when directly POSTing via AJAX.
So the response would always redirect to ``/``. If ``/`` is not a valid URL,
it would return an error. This is now fixed -- `DBAuth`_ always uses ``redirect:``.

`PPTXHandler`_ pptgen supports text styles, heatgrid order, pie/donut colors,
and a number of other features. By @sanjay.yadav

`FormHandler`_ and :py:func:`gramex.data.filter` accept a ``queryfile:``
parameter that lets you specify queries in a separate SQL file. This makes
indentation and syntax highlighting easier, making it easier to debug queries.

``gramex init`` and all Gramex installations use Yarn in offline mode if possible
- prefering Yarn over npm. This is to optimize installations.

A few developer enhancements and bugfixes:

- :py:func:`gramex.cache.open` can open XML, RSS and Atom files using lxml. It
  returns an etree object.
- All handlers support a ``handler.get_arg(key)`` method that is exactly like
  Tornado's ``handler.get_argument(key)``, but supports Unicode
- :py:func:`gramex.cache.Subprocess` waits for return code and then exits

Stats:

- Code base: 20,514 lines (gramex: 13,305, tests: 7,209)
- Test coverage: 81%


v1.23.1 (2017-11-13)
~~~~~~~~~~~~~~~~~~~~
This is an interim release with minor features and major bugfixes.

- `PPTXHandler`_ is formally released as part of Gramex, with extensive examples
  and documentation.
- `CaptureHandler`_ supports a PPTX download option that downloads image
  screenshots and pastes them into slides.
- ``gramex init`` is the new way of initializing Gramex repos. It just copies
  the minimal files required to get started, but will soon include boilerplates.
- `FileHandler`_ headers can be different for different file patterns. So within
  the same directory, you can serve different files with different content types
  and expiry using the same FileHandler. `Issue 176`_
- All auth handlers lets you `change inputs`_ using a ``prepare:`` function. You
  can decrypt browser-encrypted passwords, prefix a ``DOMAIN\`` to the username,
  or restrict access by IP. `Issue 180`_
- `Print statements`_ can be replaced by :py:func:`gramex.debug.print` - is a
  smarter replacement for ``print``. It also prints the file and line where you
  inserted the print statement, making it easier to trace flow.
- `Tracing`_ line by line execution is with the :py:func:`gramex.debug.trace()`
  decorator makes it very easy to see which lines in a function were executed.

The bugfixes are:

- Multiple Gramex instances running on the same system no longer over-write
  sessions. (This led to logouts.) `Issue 147`_
- :py:func:`gramex.cache.open` used to cache based on the file and its type, not
  arguments. So ``gramex.cache.open('data.csv', encoding='cp1252')`` and
  ``gramex.cache.open('data.csv', encoding='utf-8')`` would return the same
  cached result. This is fixed. `Issue 171`_
- `FormHandler`_ and `DBAuth`_ support tables with schemas (i.e. table names with
  dots in them, like ``schema.table``.) `Issue 185`_ and `Issue 186`_
- A bug in `watch`_ led to file permission errors on Mac systems. This is
  resolved. `Issue 183`_

Stats:

- Code base: 19,026 lines (gramex: 12,890, tests: 6,136)
- Test coverage: 65% (pptgen coverage is a gap)


v1.23.0 (2017-10-31)
~~~~~~~~~~~~~~~~~~~~
This release adds Gramex as a `Windows service`_, making it easier for Windows
administrators to auto-start and manage Gramex. Run ``gramex service install``
from the app directory to create a service.

`FormHandler`_ has improved -- you won't need FunctionHandler even to edit data.

- `FormHandler edits`_ data in databases and files. This makes it possible to
  create editable tables or settings pages.
- `FormHandler filters`_ support NULL and NOT NULL operators
- `FormHandler query`_ supports URL query parameters as values, just like filters
- `FormHandler formats`_ supports two new formats:
    - ``table`` format that is an Excel-like viewer for any data. (Future releases will allow embedding this component into templates.)
    - ``pptx`` format to download as a PPTX
- `FormHandler downloads`_ let you change the downloaded filename via ``?download=filename``
- `FormHandler queryfunction`_ lets you generate your own custom query using
  Python. Typically used for dynamically generated queries

`CaptureHandler`_ supports Chrome as a backend engine. This allows screenshots
that are far more accurate than PhantomJS.

Running ``gramex setup <directory>`` lets you `set up apps`_ by running ``npm``,
``bower``, ``pip install`` and any other relevant installations in the target
directory. This can also set up pre-installed apps like ``formhandler`` or
``capture``.

Logging is standardized. All logs are logged to ``$GRAMEXDATA/logs``. There are 3
types of logs, out-of-box:

1. `Gramex logging`_ saves all Gramex log messages on the console to ``logs/gramex.log``
2. `Request logging`_ saves all HTTP requests to ``logs/requests.csv``
3. `User logging`_ saves all login and logout actions to ``logs/user.csv``

All logs are auto-rotated weekly by default, and the location and fields can be
configured. All logging is now through the standard Python logging mechanism.

Auth handlers can now implement a "Remember me" option when users log in, and
set up different `session expiry`_ values based on the user's choice.

`LDAPAuth`_ fetches `LDAP attributes`_ with direct LDAP login. (Earlier, this was
possible only through bind LDAP login.)

`DBAuth`_ has an ``email_as`` key that sends forgot password emails from a
specific email ID.

Gramex configurations support `conditions`_. Sections will be included only in
specific environments.

`YAML imports`_ allow overriding the $YAMLURL value. This lets you mount
applications from any place into any URL. Imports also support lists.

There are several API improvements. The most important are:

- :py:func:`gramex.cache.open` guesses file type from its extension. So
  ``gramex.cache.open('data.csv')`` now works -- you don't need to specify
  ``csv`` as the second parameter.
- :py:func:`gramex.data.filter` updates the ``meta`` object to add 2 attribute:
  ``count`` which reports the number of records matched / updated, and
  ``excluded`` which reports excluded columns
- :py:class:`gramex.services.SMTPMailer` supports open email servers without
  passwords.

For security purposes, Gramex deletes all old session keys without an expiry
value. (These originate from Gramex versions prior to Gramex 1.20.)

There are several bug fixes, documentation enhancements and test cases added.

- Code base: 15,924 lines (gramex: 10,028, tests: 5,896)
- Test coverage: 79%


v1.22.0 (2017-09-28)
~~~~~~~~~~~~~~~~~~~~
This release adds Windows `IntegratedAuth`_. This allows Windows domain users to
log into Gramex automatically without entering and ID or password.

`FormHandler`_ has improved - you won't need FunctionHandler to process data.

- `FormHandler defaults`_ set up default URL query parameters that the user can override
- `FormHandler prepare`_ lets you add / modify / delete the URL query parameters dynamically
- `FormHandler query`_ can be dynamically filled with URL query parameters
- `FormHandler query`_ has a ``table:`` key. If you specify a simple query here, the results will be cached based on that query
- `FormHandler modify`_ lets you change the returned dataset before rendering

`CaptureHandler`_ supports a ``?debug=1`` URL query parameter that logs HTTP
responses and PhantomJS messages to the console. ``?debug=2`` also logs HTTP
requests made. The Guide also features a live example. CaptureHandler's
``selector`` parameter is improved and captures portions of a page better.

The default error pages shown for HTTP 500 (Internal Server Error), 404 (Not
Found) and 403 (Forbidden) are a little more informattive and better designed.

All auth handlers support a custom `session expiry`_ duration. You can increase /
decrease the cookie's expiry duration.

This release also features an undocumented `PPTXHandler`_ that generates
PowerPoint presentations. But the API will change. This handler not meant for
general use yet. A future release will define and document the specs.

There are some enhancements to the API:

- :py:func:`gramex.cache.Subprocess` returns the stdout and stderr values if no
  streams are specified
- :py:class:`gramex.transforms.twitterstream.TwitterStream` supports a ``flush=``
  option that saves the stream data periodically
- :py:func:`gramex.cache.query` does not cache queries by default. It caches only
  if a ``state=`` is specified. (This may change.)
- :py:func:`gramex.data.filter` ignores empty query parameters, which is the
  expected behaviour

There are some changes to Gramex behaviour that may impact your application:

- `UploadHandler`_ backup file naming has changed from ``name.ext.<time>`` to ``name.<time>.ext``
- The `deploy yaml`_ configuration hides the ``Server:`` HTTP header for security
- `Google Auth`_ stores the email ID of the user as the user ID, not the Google provided ID
- All handlers have a ``handler.kwargs`` attribute that has the ``kwargs:`` configuration passed to the handler

Stats:

- Code base: 14,765 lines (gramex: 9,278, tests: 5,487)
- Test coverage: 79%


v1.21.0 (2017-08-29)
~~~~~~~~~~~~~~~~~~~~
This is a major release with new functionality. There are two new handlers.

- `CaptureHandler`_ takes image screenshots and PDF downloads from Gramex. It
  uses PhantomJS behind the scenes. Future releases will allow Chrome headless.
- `FormHandler`_ is a simplified replacement for `DataHandler`_ and
  `QueryHandler`_. If you want to expose data from any file or database after
  transforming it, use `FormHandler`_.

`UploadHandler`_ is also improved. Specifically:

- You can `overwrite uploads`_ in the way you want.
- You can customise the `uploaded filename`_.

All requests are now logged under ``$GRAMEXDATA/logs/requests.csv``, independent
of the console display. This will be used in the next release to show app usage.

When writing code, there are a few new features:

- `YAML imports`_ are simplified. You can now write ``import: filename.yaml``
  instead of ``import: {key: filename.yaml}``.
- It's easier to `parse URL arguments`_ inside `FunctionHandler`_. All handlers
  have a ``handler.args`` dict that has the URL arguments. ``?x=1`` sets
  ``handlers.args`` to ``{'x': ["1"]}``. Unlike Tornado's ``.get_arguments()``,
  this supports Unicode keys.
- You can also `parse URL arguments`_ using ``handler.argparse()``, which lets
  you convert arguments to the right type, restrict values and so on.
- You can convert GET requests to POST, PUT or DELETE via  `method overrides`_.
  This works on ANY handler. Add a ``X-HTTP-Method-Override: POST`` header or
  ``?x-http-method-override=POST`` to the URL to convert GET to POST.
- :py:func:`gramex.data.filter` lets you filter DataFrames using URL arguments.
  This is the powerful filtering mechanism behind `FormHandler`_.
- :py:func:`gramex.data.download` helps create downloadable CSV, XLSX, JSON or
  HTML files from one or more DataFrames.
- When running a subprocess, use :py:func:`gramex.cache.Subprocess`. This is an
  async method and does not block other requests.
- ``gramex.conf.variables.GRAMEXPATH`` can be used to identify the PATH where
  Gramex source libraries are located.

Documentation is also improved to cover:

- Sending `email attachments`_ and `command line emails`_
- Accessing `predefined variables`_ from a FunctionHandler
- Deploying an `nginx reverse proxy`_ server

There are a number of bugfixes on this release. The most important are:

- This release works on Python 3 as well. (The previous release 1.20 did not.)
- Session keys can contain Unicode characters. (Earlier, this raised an error.)
- :py:func:`gramex.cache.open` returns separate results for different transforms
- If the ``log:`` configuration has an error, Gramex does not stop working

There is one deprecation this release. ``handler.kwargs`` is now
``handler.conf.kwargs``. (This is a largely unused feature of Gramex.) UPDATE:
this was re-introduced in 1.22.


v1.20.0 (2017-07-31)
~~~~~~~~~~~~~~~~~~~~
This is a major release with some critical enhancements and fixes.

(NOTE: This release supports Python 2, not Python 3 due to a temporary bug.)

Firstly, caching is improved.

- :py:func:`gramex.cache.open` accepts a ``transform=`` parameters that lets you
  post-process the returned result. ``gramex.cache.open('data.xlsx', 'xlsx',
  transform=process_data)`` ensures that ``process_data(data)`` is called only if
  the ``data.xlsx`` has changed.
- :py:func:`gramex.cache.open` supports a ``rel=True`` parameter. If specified,
  it loads the file from the path relative to the calling file. So if
  ``module.py`` calls ``gramex.cache.open('data.xlsx', 'xlsx', rel=True)`` loads
  ``data.xlsx`` in the same directory as ``module.py``, not relative to gramex.
- :py:func:`gramex.cache.open` supports a ``'config'`` mode that loads YAML files
  just like Gramex does -- i.e. with environment variables support, and returning
  the values as AttrDict instead of dict.

Gramex supports inline images in HTML `email`_. This is useful when sending
visualizations as images in emails.

There is better support for programmatic authentication.

- The ``X-Gramex-Key`` header lets you `override users`_ by specifying an
  encrypted JSON object for the user. (Documentation pending)
- `OTP`_ (one-time passwords) are now available.
- The ``password:`` function in `DBAuth`_ can now accept a ``handler`` object
  apart from the ``content`` (which is the password)

There are a few security enhancements.

- `DBAuth`_ and `SimpleAuth`_ delay the response on repeated login failures.
  You can specify the ``delay:`` in ``gramex.yaml``.
- Every time the user logs in, the session ID changes. This avoids
  `session fixation`_.
- The session ID cookie uses `HttpOnly`_ cookies. If the request is made on
  HTTPS, it also uses `Secure`_ cookies.

The performance of sessions has been improved as well.

- Sessions stores were constantly polled to see if they had changed. This drains
  the CPU. Now, changes are tracked. Sessions are saved only if there are
  changes.
- Expired sessions are cleared on the server. So the session store will no longer
  bloat indefinitely.

Command line usage of Gramex is improved.

- ``gramex --help`` shows Gramex command line usage. ``gramex -V`` shows the version.
- On startup, Gramex informs users of keyboard shortcuts available (``Ctrl+B`` for opening the browser and ``Ctrl+D`` for debugging.)
- Gramex warns you when ``url:`` sections have duplicate keys, and override one
  another. This helps when running on shared instances like ``uat.gramener.com``.
- When loading a module (e.g. from a `FunctionHandler`_), it would not get reloaded
  if it had an error. This is fixed.

There are a couple of obscure fixes to `DataHandler`_.

- `DataHandler`_ no longer raises an error if you have empty values in queries,
  like ``?city=``.
- `DataHandler`_ has an undocumented ``posttransform`` method. It now works for
  PUT method as well as POST, but continues to be undocumented.

Finally, there are a few documentation updates.

- A detailed `line profile`_ example is available.
- All `exercises`_ have been consolidated into a single page.


v1.19.0 (2017-07-09)
~~~~~~~~~~~~~~~~~~~~
This is a minor enhancement release with

- There was a bug where sessions were not being flushed, forcing users to log in
  when Gramex is restarted. This if fixed.
  `#84 <https://code.gramener.com/s.anand/gramex/issues/84>`_
- Instead of using ``args:`` and ``kwargs:`` in gramex.yaml, you can now use
  ``function: method(arg, arg, key=val, ...)``.
- The user interface of the default login templates is improved. Here is the new
  `DBAuth login template`_.
- `Reloading`_ of configurations, modules and files is seamless. You don't need
  to restart Gramex when your Python code or templates change.
- `Query caching`_ via :py:func:`gramex.cache.query` caches SQL query results
- `DataHandler templates`_ and `QueryHandler templates`_ let you customize the
  output of these handlers arbitrarily
- :py:func:`gramex.cache.open` supports new formats: ``md`` for Markdown, ``xls`` or
  ``xlsx`` for Excel, and ``template`` for Tornado templates.
- :py:func:`gramex.cache.opener` makes it easier to create callbacks for
  :py:func:`gramex.cache.open`.
- :py:class:`gramex.config.CustomEncoder` is a custom JSON encoder that encodes
  objects that contain DataFrames. This makes it easy to JSON dump objects that
  contain DataFrames.
- The `deploy yaml`_ configuration now protects against XSS attacks as well.
- If Gramex is re-installed in a different location, the guide does not load. The
  error message now asks the user to uninstall the guide.
  `#76 <https://code.gramener.com/s.anand/gramex/issues/76>`_


v1.18.0 (2017-06-29)
~~~~~~~~~~~~~~~~~~~~
This is a minor enhancement release with several critical bugfixes.

- This version requires Anaconda 4.4.0. It also requires recent ldap3 and
  psycopg2 versions. Please upgrade by running ``conda update conda`` and then
  ``conda update anaconda``.
- `Installation`_ is simpler. It's a one-line install using ``pip`` (no ``conda``).
- Gramex runs on Python 3.6 (as well as Python 3.5 and 2.7)
- `Module caching`_ is now available via :py:func:`gramex.cache.reload_module()`.
  You can refresh Python files without restarting Gramex.
- `Data caching`_ is more robust. It checks file sizes in addition to the
  timestamp. :py:func:`gramex.cache.open()` now supports loading Tornado
  templates, apart from various data / text files. It also supports loading the
  same file via multiple callbacks (e.g. loading a CSV file as ``csv`` and
  ``text``.)
- `Login templates`_ are now reloaded every time the template changes.
- Access logs enabled by default. These are weekly CSV files stored at:
  - Windows: %LOCALAPPDATA%\Gramex Data\logs\access.csv
  - Linux: ~/.config/gramexdata/logs/access.csv
  - OS X: ~/Library/Application Support/Gramex Data/logs/access.csv
- `YAML imports`_ allow namespaces. You mostly won't need this. But if you're
  running multiple apps, this avoid conflict between URLs defined in each.
- `QueryHandler`_ has some bugfixes. If you have multiple queries, and only some
  of them use URL query parameters are arguments, it no longer fails. It also
  does not crash if the query returns no results.
- `FileHandler`_ was checking URLs against ``allow:`` and ``ignore:``. It should
  have been checking file paths. As a result, the `deploy yaml`_ was disabling
  sub-directories. Also, the `deploy yaml`_ file was not getting installed. Both
  are fixed.
- Several sections have improved documentation.
  `Offline install`_.
  `HTML email`_.
  `Reusing configurations`_.
  `Static file caching`_.


v1.17.1 (2017-04-23)
~~~~~~~~~~~~~~~~~~~~
This is a maintenance release with a few minor enhancements:

- `TwitterRESTHandler`_ and `FacebookGraphHandler`_ use GET request by default.
  This used to be the POST request. This is a **breaking change**.
- Access token on `TwitterRESTHandler`_ and `FacebookGraphHandler`_ are persisted

A series of important bugfixes are addressed:

- Tornado 4.5 routing module uses a ``tornado.routing.Router`` Class instead of
  handlers. This requires an alternate way of clearing existing handlers.
- `scandir` requires a C-compiler to install. Change docs and setup script to
  avoid upgrading libraries (particularly scandir) via ``--upgrade`` when running
  pip install.
- HTTP 304 requests (i.e. cached requests) preserve and re-send the same headers
  as the original response


v1.17 (2017-01-29)
~~~~~~~~~~~~~~~~~~

This version has a breaking change. The default login URL is ``/login/`` instead
of ``/login``. This makes it easier to create custom login pages using
FileHandler (e.g. ``/login/index.html``). If your application breaks, in your
gramex.yaml ``app:`` section, add ``login_url: /login`` to revert the change.

- `WebSocketHandler`_ lets you create websocket servers on Gramex.
- `DataHandler`_ and `QueryHandler`_ support the ``?filename=`` parameter to specify a download filename
- Several enhancements to authentication including:
    - Each URL can have its own `login URL`_ via a ``login_url:`` key.
    - `Roles`_ membership can be checked through multiple AND / OR combinations
    - `Google Auth`_ now allows accessing logged-in users' Google data
    - Auth handlers' `auth redirection`_ supports ``?next=`` by default
    - `Login templates`_ are documented
    - `SimpleAuth`_ now lets you add other attributes (e.g. roles) to the user object
- `Data caching`_ is easier with the :py:func:`gramex.cache.open()` method
- A major bug related to `watch`_ is fixed.
- Some bugs related to JSONStore (used for session storage) are fixed


v1.16 (2016-10-16)
~~~~~~~~~~~~~~~~~~

- Add a `deploy yaml`_ configuration that makes your deployment automatically more secure
- `QueryHandler`_ supports INSERT/UPDATE/DELETE statements as well via POST requests.
- The `email`_ service accepts [attachments from strings](https://learn.gramener.com/gramex/gramex.services.html#gramex.services.emailer.message)
- `LDAPAuth`_ can [bind as an admin](https://learn.gramener.com/guide/auth/#bind-ldap-login) and log in as any user
- Configuration in the ``handlers:`` section percolates to other handlers
- `UploadHandler`_ transforms accept handler as a second cargument in addition to metadata
- Fixed bugs to improve security, reduce the CPU usage, better JSON handling for binary data, HDF5store corruption, multiple email recipients, caching 304 responses,


v1.15 (2016-08-21)
~~~~~~~~~~~~~~~~~~

- `DataHandler`_ supports a ``?q=`` parameter that searches all text columns
- `QueryHandler`_ supports multiple SQL queries in a single request
- `DataHandler`_ and `QueryHandler`_ support a ``?format=xlsx`` to download as
  Excel. In QueryHandler, multiple SQL queries translate to multiple sheets
- `TwitterStream`_ scheduler can now write to SQLAlchemy databases, as well as
  run a custom function when it receives a tweet
- The `watch`_ service supports wildcards and directories in paths. You can watch
  for changes to a pattern of files or any files under a directory
- :py:func:`gramex.transforms.flattener` transform that flattens JSON hierarchies based
  on a custom field mapping
- :py:func:`gramex.init` supports a ``force_reload=True`` that reloads services.
  To support this, :py:func:`gramex.transforms.build_transform` is no longer cached.

v1.14 (2016-08-11)
~~~~~~~~~~~~~~~~~~

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


v1.13 (2016-08-01)
~~~~~~~~~~~~~~~~~~

- All handlers support custom `error handlers`_. You can show custom 404, 500
  pages.
- `SimpleAuth`_ is an extremely simple login handler you can use for testing
- `ProcessHandler`_ supports the ``redirect:`` config (used by many handlers)
  to redirect the user after the process is executed.
- `DataHandler`_ supports a ``thread: false``. This switches to a synchronous
  version that is (currently) less buggy.
- Variables can be assigned different values in different environments via a
  simple `conditional variables`_ syntax.

v1.12 (2016-07-21)
~~~~~~~~~~~~~~~~~~

* `DBAuth`_ features a forgot password feature.
* `FileHandler`_ supports ``POST`` and other HTTP methods via the ``methods:``
  configuration. ``POST`` is now available by default.
* The ``cache:`` key supports user attributes. You can cache responses based on
  the user.
* Gramex loads a bit faster by importing slow modules (e.g. Pandas) only if
  required.

v1.11 (2016-07-15)
~~~~~~~~~~~~~~~~~~

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

v1.10 (2016-07-01)
~~~~~~~~~~~~~~~~~~

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


v1.0.9 (2016-06-15)
~~~~~~~~~~~~~~~~~~~

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

v1.0.8 (2016-06-01)
~~~~~~~~~~~~~~~~~~~

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


v1.0.7 (2016-05-15)
~~~~~~~~~~~~~~~~~~~

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


v1.0.6 (2016-05-01)
~~~~~~~~~~~~~~~~~~~

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
* `DataHandler`_ is now asynchronous. Requests won't be blocked while queries run.
* `ProcessHandler`_ accepts ``stdout`` and ``stderr`` parameters. These can be
  ``false`` to ignore the output, or set to any file name (to save the output /
  errors in that file.) The default for ``stdout`` and ``stderr`` is ``pipe``,
  which sends the output to the browser.
* Gramex defers loading of services to ensure a faster initial loading time.
* Gramex guide is a part of Gramex. There's no need to install it separately.


v1.0.5 (2016-04-15)
~~~~~~~~~~~~~~~~~~~

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
* `ProcessHandler`_ implemented. It runs any program as a sub-process and
  streams the output to the request.
* `FunctionHandler`_ accepts co-routines for asynchronous processing. Functions
  can also ``yield`` strings that will be immediately written and flushed,
  providing a streaming interface.
* `FileHandler`_ accepts multiple ``path`` as an array. The output of these
  files are concatenated after transformated.
* In the `FileHandler`_ config, you can use ``pattern: /abc`` instead of
  ``pattern: /(abc)`` if you are mapping a single URL to a single path.
* `FileHandler`_ supports ``function: template`` in the transforms section.
  This treats the file as a tornado template and renders the output.
* `FileHandler`_ directory listing looks prettier now.
* `DataHandler`_ supports ``like`` and ``notlike`` operations.
* The `watch`_ section of ``gramex.yaml`` allows you to trigger events when
  files are changed.


v1.0.4 (2016-03-30)
~~~~~~~~~~~~~~~~~~~

* `FunctionHandler`_ supports co-routines and works asynchronously
* `FileHandler`_ is the new name for ``DirectoryHandler`` (both will work)
* Implement authentication via Google, Twitter and Facebook OAuth
* Simpler installation steps


v1.0.3 (2016-01-18)
~~~~~~~~~~~~~~~~~~~

* Implement `DataHandler`_ that displays data from databases (via
  `SQLAlchemy <http://www.sqlalchemy.org/>`__ and `Blaze <http://blaze.pydata.org/>`__)
* ``DirectoryHandler``:
    - lets gramex.yaml specify input file encoding (defaults to UTF-8)
    - takes both content as well as the handler as input
* gramex.yaml URL priority can be specified explicitly using ``priority:``

v1.0.2 (2015-10-11)
~~~~~~~~~~~~~~~~~~~

* Implement `FunctionHandler`_ that renders any function
* ``DirectoryHandler`` transforms files (e.g. converting Markdown or YAML to
  HTML)
* ``gramex.transforms.badgerfish`` transform converts YAML to HTML
* When a configuration file is changed, it is reloaded immediately
* Document Gramex at https://learn.gramener.com/gramex/
* Add test cases for handlers

v1.0.1 (2015-09-09)
~~~~~~~~~~~~~~~~~~~

* Is a directory-browsing webserver (``gramex.handlers.DirectoryHandler``)
* Works with Python 3 in addition to Python 2
* Add test cases with full coverage for ``gramex.config`` and
  ``gramex.confutil``
* Logs display friendly dates, and absolute paths instead of relative paths

v1.0.0 (2015-09-08)
~~~~~~~~~~~~~~~~~~~

* First release of core server


.. _Firebase API: https://www.firebase.com/docs/rest/api/
.. _FunctionHandler: https://learn.gramener.com/guide/functionhandler/
.. _JSONHandler: https://learn.gramener.com/guide/jsonhandler/
.. _FileHandler: https://learn.gramener.com/guide/filehandler/
.. _DataHandler: https://learn.gramener.com/guide/datahandler/
.. _ProcessHandler: https://learn.gramener.com/guide/processhandler/
.. _QueryHandler: https://learn.gramener.com/guide/queryhandler/
.. _TwitterRESTHandler: https://learn.gramener.com/guide/twitterresthandler/
.. _FacebookGraphHandler: https://learn.gramener.com/guide/facebookgraphhandler/
.. _LogoutHandler: https://learn.gramener.com/guide/auth/#log-out
.. _WebSocketHandler: https://learn.gramener.com/guide/websockethandler/
.. _LDAPAuth: https://learn.gramener.com/guide/auth/#ldap
.. _LDAP attributes: https://learn.gramener.com/guide/auth/#ldap-attributes
.. _Google Auth: https://learn.gramener.com/guide/auth/#google-auth
.. _DBAuth: https://learn.gramener.com/guide/auth/#database-auth
.. _SimpleAuth: https://learn.gramener.com/guide/auth/#simple-auth
.. _TwitterAuth: https://learn.gramener.com/guide/auth/#twitter-auth
.. _IntegratedAuth: https://learn.gramener.com/guide/auth/#integrated-auth
.. _SAMLAuth: https://learn.gramener.com/guide/auth/#SAML-auth
.. _session expiry: https://learn.gramener.com/guide/auth/#session-expiry
.. _TwitterStream: https://learn.gramener.com/guide/twitterresthandler/#twitter-streaming
.. _UploadHandler: https://learn.gramener.com/guide/uploadhandler/
.. _CaptureHandler: https://learn.gramener.com/guide/capturehandler/
.. _PPTXHandler: https://learn.gramener.com/guide/pptxhandler/
.. _FormHandler: https://learn.gramener.com/guide/formhandler/
.. _FormHandler filters: https://learn.gramener.com/guide/formhandler/#formhandler-filters
.. _FormHandler tables: https://learn.gramener.com/guide/formhandler/#formhandler-tables
.. _FormHandler charts: https://learn.gramener.com/guide/formhandler/#formhandler-charts
.. _FormHandler downloads: https://learn.gramener.com/guide/formhandler/#formhandler-downloads
.. _FormHandler defaults: https://learn.gramener.com/guide/formhandler/#formhandler-defaults
.. _FormHandler prepare: https://learn.gramener.com/guide/formhandler/#formhandler-prepare
.. _FormHandler query: https://learn.gramener.com/guide/formhandler/#formhandler-query
.. _FormHandler queryfunction: https://learn.gramener.com/guide/formhandler/#formhandler-queryfunction
.. _FormHandler modify: https://learn.gramener.com/guide/formhandler/#formhandler-modify
.. _FormHandler formats: https://learn.gramener.com/guide/formhandler/#formhandler-formats
.. _FormHandler edits: https://learn.gramener.com/guide/formhandler/#formhandler-edits
.. _FormHandler parameters: https://learn.gramener.com/guide/formhandler/#formhandler-parameters
.. _FormHandler headers: https://learn.gramener.com/guide/formhandler/#custom-http-headers
.. _caching: https://learn.gramener.com/guide/cache/
.. _scheduler: https://learn.gramener.com/guide/scheduler/
.. _log: https://learn.gramener.com/guide/config/#logging
.. _Gramex logging: https://learn.gramener.com/guide/config/#logging
.. _Request logging: https://learn.gramener.com/guide/config/#request-logging
.. _User logging: https://learn.gramener.com/guide/config/#user-logging
.. _conditions: https://learn.gramener.com/guide/config/#conditions
.. _apps: https://learn.gramener.com/guide/apps/
.. _set up apps: https://learn.gramener.com/guide/apps/#setting-up-apps
.. _debug: https://learn.gramener.com/guide/debug/
.. _sessions: https://learn.gramener.com/guide/auth/#sessions
.. _login actions: https://learn.gramener.com/guide/auth/#login-actions
.. _auth logging: https://learn.gramener.com/guide/auth/#logging
.. _authorization: https://learn.gramener.com/guide/auth/#authorization
.. _Gramex update page: https://gramener.com/gramex-update/
.. _ignore files: https://learn.gramener.com/guide/filehandler/#ignore-files
.. _auth redirection: https://learn.gramener.com/guide/config/#redirection
.. _change inputs: https://learn.gramener.com/guide/auth/#change-inputs
.. _email: https://learn.gramener.com/guide/email/
.. _conditional variables: https://learn.gramener.com/guide/config/#conditional-variables
.. _error handlers: https://learn.gramener.com/guide/config/#error-handlers
.. _watch: https://learn.gramener.com/guide/watch/
.. _deploy yaml: https://learn.gramener.com/guide/deploy/#security
.. _Login templates: https://learn.gramener.com/guide/auth/#login-templates
.. _login URL: https://learn.gramener.com/guide/auth/#login-urls
.. _Roles: https://learn.gramener.com/guide/auth/#roles
.. _Data caching: https://learn.gramener.com/guide/cache/#data-caching
.. _Module caching: https://learn.gramener.com/guide/cache/#module-caching
.. _YAML imports: https://learn.gramener.com/guide/config/#yaml-imports
.. _Installation: https://learn.gramener.com/guide/install/
.. _Offline install: https://learn.gramener.com/guide/install/#offline-install
.. _HTML email: https://learn.gramener.com/guide/email/#html-email
.. _Reusing configurations: https://learn.gramener.com/guide/config/#reusing-configurations
.. _Static file caching: https://learn.gramener.com/guide/cache/#cache-static-files
.. _query caching: https://learn.gramener.com/guide/cache/#query-caching
.. _DataHandler templates: https://learn.gramener.com/guide/datahandler/#datahandler-templates
.. _QueryHandler templates: https://learn.gramener.com/guide/queryhandler/#queryhandler-templates
.. _Reloading: https://learn.gramener.com/guide/debug/#reloading
.. _DBAuth login template: https://learn.gramener.com/guide/auth/dbsimple
.. _session fixation: https://www.owasp.org/index.php/Session_fixation
.. _HttpOnly: https://www.owasp.org/index.php/HttpOnly
.. _Secure: https://www.owasp.org/index.php/SecureFlag
.. _override users: https://learn.gramener.com/guide/auth/#encrypted-user
.. _OTP: https://learn.gramener.com/guide/auth/#otp
.. _exercises: https://learn.gramener.com/guide/exercises/
.. _line profile: https://learn.gramener.com/guide/debug/#line-profile
.. _overwrite uploads: https://learn.gramener.com/guide/uploadhandler/#overwriting-uploads
.. _uploaded filename: https://learn.gramener.com/guide/uploadhandler/#saving-uploads
.. _BaseHandler attributes: https://learn.gramener.com/guide/handlers/#basehandler-attributes
.. _parse URL arguments: https://learn.gramener.com/guide/functionhandler/#parse-url-arguments
.. _method overrides: https://learn.gramener.com/guide/jsonhandler/#method-override
.. _email attachments: https://learn.gramener.com/guide/email/#email-attachments
.. _command line emails: https://learn.gramener.com/guide/email/#command-line-emails
.. _predefined variables: https://learn.gramener.com/guide/config/#predefined-variables
.. _nginx reverse proxy: https://learn.gramener.com/guide/deploy/#nginx-reverse-proxy
.. _Windows service: https://learn.gramener.com/guide/deploy/#windows-service
.. _Print statements: https://learn.gramener.com/guide/debug/#print-statements
.. _Tracing: https://learn.gramener.com/guide/debug/#tracing
.. _change inputs: https://learn.gramener.com/guide/auth/#change-inputs
.. _Issue 147: https://code.gramener.com/s.anand/gramex/issues/147
.. _Issue 171: https://code.gramener.com/s.anand/gramex/issues/171
.. _Issue 176: https://code.gramener.com/s.anand/gramex/issues/176
.. _Issue 180: https://code.gramener.com/s.anand/gramex/issues/180
.. _Issue 183: https://code.gramener.com/s.anand/gramex/issues/183
.. _Issue 185: https://code.gramener.com/s.anand/gramex/issues/185
.. _Issue 186: https://code.gramener.com/s.anand/gramex/issues/186
.. _UI component library: https://learn.gramener.com/guide/uicomponents/
.. _inactive expiry: https://learn.gramener.com/guide/auth/#inactive-expiry
.. _Sign up: https://learn.gramener.com/guide/auth/#sign-up
.. _node: https://nodejs.org/
.. _Smart Alerts: https://learn.gramener.com/guide/alert/
.. _Alerts command line: https://learn.gramener.com/guide/alert/#alert-command-line
.. _Log viewer: https://learn.gramener.com/guide/logviewer/
.. _Leaflet: http://leafletjs.com/
.. _topojson: https://github.com/topojson/topojson
.. _shepherd: http://github.hubspot.com/shepherd/docs/welcome/
.. _select2: https://select2.org/
.. _g1: https://www.npmjs.com/package/g1
.. _Ripples: https://learn.gramener.com/guide/uicomponents/#ripples
.. _Background: https://learn.gramener.com/guide/uicomponents/#background
.. _Gradient: https://learn.gramener.com/guide/uicomponents/#gradient
.. _bandit: https://github.com/openstack/bandit/
.. _Bootstrap 4 Beta 3: https://blog.getbootstrap.com/2017/12/28/bootstrap-4-beta-3/
.. _Bootstrap 4: https://blog.getbootstrap.com/2018/01/18/bootstrap-4/
.. _session data: https://learn.gramener.com/guide/auth/#session-data
.. _docker install: https://learn.gramener.com/guide/install/#docker-install
.. _Windows administration: https://learn.gramener.com/guide/deploy/#windows-administration
.. _AJAX login: https://learn.gramener.com/guide/auth/#ajax-login
.. _Seaborn: https://seaborn.pydata.org/
.. _numeral.js: http://numeraljs.com/
.. _deploy: https://learn.gramener.com/guide/deploy
.. _ProxyHandler: https://learn.gramener.com/guide/proxyhandler/
.. _How XSRF works: https://learn.gramener.com/guide/filehandler/#how-xsrf-works
.. _v1.30 release notes: https://learn.gramener.com/guide/release/1.30/
.. _v1.31 release notes: https://learn.gramener.com/guide/release/1.31/
.. _v1.32 release notes: https://learn.gramener.com/guide/release/1.32/
.. _v1.33 release notes: https://learn.gramener.com/guide/release/1.33/
.. _v1.34 release notes: https://learn.gramener.com/guide/release/1.34/
.. _v1.35 release notes: https://learn.gramener.com/guide/release/1.35/
