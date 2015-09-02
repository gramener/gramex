Gramex 1.0
================================================================================

Gramex 1.0 is a backward-incompatible re-boot of the visualisation platform.

- *Why 1.0* We use semantic versioning. `1.0` means we have a published API that
  we follow.
- *Why backward-incompatible* There are many bad practices that Gramex 0.x
  encourages that we want to break-away from. For example, inconsistent
  attributes in chart components.

This is the work-in-progress design.

Principles
--------------------------------------------------------------------------------

These are the core principles of Gramex.

1. **Data, not code** We modify data to change the functionality of the
   application, wherever posssible. Code is written only as a last resort,
   either to provide very niche (and rare) functionality, or to cover a large
   number of general-purpose cases.
1. **Modular licensing**. It can be broken down into smaller parts that can be
   licensed independently, with customisable trials.

These are proposed principles, for discussion.

1. **User-friendly* at every stage. Move from code to data. From data to GUI.
   From GUI to live editing.
1. **Lazy computations**. Defer computation to as late as possible.
1. **Modular**. Its parts can be used independently. It can use third party
   modules easily.
1. **Automated reloads**. Configurations are reloaded transparently.
1. **RESTful**. Use REST APIs and friendly URLs.
1. **YAML** for configuration, not XML (too verbose), or JSON (too strict, no
   comments).

Architecture
--------------------------------------------------------------------------------

Gramex has:

- **A core server**, which provides a variety of services (via Python libraries)
  to the entire application.
- **Handlers**, which handle specific URL patterns as required. They may show
  templates, act as a websocket, provide a data interface, serve static files,
  etc.
- **Components**, which can be used by handlers to render certain kinds of
  outputs.

Server
--------------------------------------------------------------------------------

The server is the core engine of Gramex. It offers services such as URL mapping,
logging, caching, etc that applications use.

The server is configured by layered config files. The server has a default
`gramex.yaml`. Gramex runs in a home directory, which can have a `gramex.yaml`,
and can define other config files that further over-ride it.

Configurations are loaded as [ordered attrdicts][lya] files and stored in the
variable `gramex.config`. Apps can update this and run `gramex.reconfigure()` to
update all configurations (except `app:` and `conf:`).

[lya]: https://github.com/mk-fg/layered-yaml-attrdict-config

Configurations are pure YAML, and do not have any tags. The YAML files are
grouped into one section per service:

    version: 1.0    # Gramex and API version
    conf: ...       # Configuration files
    app: ...        # Main app configuration section
    url: ...        # URL mapping section
    log: ...        # Logging configuration
    cache: ...      # Caching configuration
    email: ...      # Email configuration
    ...             # etc. -- one section per service

The server provides an admin view that allows admins to see (and modify) the
configurations. (It does not show the history or source of the setting, though.)

The server is asynchronous. It executes on an event loop that applications can
use (for deferred execution, for example). The server also runs a separate
thread that can:

- Interrupt long requests, even without the consent of the app. (For example, if
  the connection closes, just stop the function.)
- Re-load changed config files into memory
- Deferred logging
- etc.

However, all request handlers will run on a single thread, since Tornado
[RequestHandler is not thread-safe](thread-safety).

[thread-safety]: http://tornado.readthedocs.org/en/latest/web.html#thread-safety-notes

### Conf

`gramex.yaml` file may have a `conf:` section that lists additional YAML
configurations.

    conf:                           # Load additional configurations
      app:                          # ... into the app: section from:
        subapps: */gramex.yaml      #   All gramex.yaml under 1st-level dir
      url:                          # ... into the url: section from:
        subapps: */gramex.url.yaml  #   All gramex.url.yaml under 1st-level dir
        xyz: d:/xyz/gramex.url.yaml #   A specific gramex.url.yaml file
      log:                          # ... into the log: section from:
        ...                         #   etc

This is not recursive. If the `conf:` section has a `conf:` sub-section, it is
ignored.

Set a value to `!!null` to delete it. Keys with a `!!null` value are dropped
after parsing.

Relative paths?

### App

The `app:` section defines the settings for the [Tornado app](app-settings).

[app-settings](http://tornado.readthedocs.org/en/stable/web.html#tornado.web.Application.settings)

    app:
      listen: 8888              # Port to bind to
      default_host: ...         # Optional name of default host
      settings:                 # Tornado app settings
        autoreload: True
        debug: True
        etc.

Only settings that can be specified in YAML are allowed, not settings that
require Python.

### URL

[urlspec]: http://tornado.readthedocs.org/en/stable/web.html#tornado.web.URLSpec

The `url:` section maps URL patterns to handlers (via [URLSpec](urlspec)). For
example, this resets the application's handlers to a single handler. The key
`app:` is the `name` for the `URLSpec`.

    url:                                    # Main URL mapping section
      app:                                  # A unique name for this handler
        pattern: /app/.*                    # All URLs beginning with /app/
        handler: TemplateHandler            # Handles templates
        kwargs:                             # Options passed to handler
          - path: d:/app/

Gramex will have handlers for handling data (e.g. Data API), auth (OAuth, SAML,
etc), logging, websockets, etc.

### Log

The `log:` section defines the log handlers. It uses the same structure as
the Python [logging schema](logging-schema)

[logging-schema]: https://docs.python.org/2/library/logging.config.html#logging-config-dictschema

By default, the system `gramex.yaml` has a log handler called `admin` that logs
events for the admin page to display and filter.

### Error

The `error:` section defines how errors are handled. It defines a set of keys.
When a `GramexError` is raised with a specific key, the appopriate error handler
is triggered.

    error:
        page-not-found:
            code: 404
            function: SimpleErrorPage
            kwargs:
              h1: Page not found
              body: This is not the page you are looking for
        custom-error:
            code: 500
            function: ErrorTemplateHandler
            path: 500.html

The `function:` is called from [RequestHandler write_error()][write-error] as
`function(handler, status_code, **kwargs)`. In addition the provided `kwargs`,
an `exc_info` triple will be available as `kwargs['exc_info']`.

[write-error]: http://tornado.readthedocs.org/en/latest/web.html#tornado.web.RequestHandler.write_error


### Schedule

The `schedule:` section defines when specific code is to run.

    schedule:
      some-scheduler-name:
        times:                              # Follows cron structure
          minutes: 0, 59, *, 30-40/5
          hours: 3
          dates: *, L
          months: *, jan, 1,
          weekdays: *
          years: *
        startup: true                 # In addition, run on startup
        function:
        kwargs: module.function

Use [parse-crontab](https://github.com/josiahcarlson/parse-crontab) to parse.

All default services provided by Gramex are part of the scheduler. For example,
`gramex.yaml` configurations are reloaded every 5 minutes.

    schedule:
      gramex-config:
        times:
          minutes: */5
        function: gramex.reload_config

### License

The licensing mechanism handles the following scenarios:

- I only want to sell only the treemap application
- I only want SAML Auth, not OAuth
- I only want visual, not analytic components
- Only single user license

How are services, handlers and components identified?

The license configuration looks like this:

    license:
      default:                    # Name of license. (Multiple licenses possible)
        key: ...                  # License key for this license
        systems:                  # Systems this license is valid for
          system-1:               # Name of the first system
            method:               #   Algorithm used to compute the sysid
            sysid:                #   System's unique ID based on algorithm
          system-2:               # Name of the second system
            method:               #   Algorithm used to compute next sysid
            sysid:                #   ...
        validity:                 # From when to when is the license valid
          start: !!timestamp 2015-01-01T00:00:00Z
          end:   !!timestamp 2016-01-01T00:00:00Z
        users: 1                  # Optional: max users allowed
        inventory:                # What's allwoed. (Values matter; keys are just labels)
          treemap:                # Each permission is a key
            services:             #   Allowed services
              ...                 #     How to define these?
            handlers:             #   Allowed handlers
              ...                 #     How to define these?

### Services

- **Caching**
    - Output follows HTTP caching policy. Server acts as a caching HTTP proxy.
    - Any structure can be cached and re-used across apps
    - Any structure can be uniquely identified, possibly served as a URL
    - Cache management: Delete LRU (least recently used), LFU (least frequently
      used), etc. Based on memory / disk availability.
    - Cache storage: memory, disk (serialization)
    - Cache expiry, re-creation
    - Cache must be thread-safe
    - Cache record:
      - Namespace
      - Last updated
      - Context (e.g. user)
      - Hits (how often was this record retrieved)
      - Data
      - How to compute the data

- **Rendering** components to PDF, PPTX, PNG, SVG, etc.
- **Computation workflow**.
- **Communication**. Emails, etc
- **Queues**: If dataframes have to be stored, for example, and we want to avoid
  too many dataframes being stored. Or if we need a cache with a limited memory
  usage.


### Other services

These services are **NOT** provided by Gramex.

- **Distributed computing** is handled by the apps themselves. This can be via
  an external computing engine (e.g. Spark) or one that is custom-built.
- **Load balancing** is handled by a front-end balancer (e.g. nginx).

References:

- [Ben Darnell's template plans for Tornado 4.1](https://groups.google.com/forum/?fromgroups#!searchin/python-tornado/template$20asynchronous%7Csort:date/python-tornado/Eoyb2wphJ-o/fj9EAb166PIJ)
- [`asynchronous` directive pull request](https://github.com/tornadoweb/tornado/pull/553)
- [`coroutine=` parameter pull request](https://github.com/tornadoweb/tornado/pull/1311)

Handlers
--------------------------------------------------------------------------------

- **Namespaced app folders**.
    - Reserved namespaces
    - Add a directory `app/`, and the URL mappings for `/app/...` will be taken
      from the `app/` directory.
    - With `/app/` there is full flexibility on how to handle the URLs
    - No URLs outside `/app/` will be affected.
    - Configurations use data, not code. (e.g. YAML, not Python)
- **Data store**. Perhaps using an API like
  [Webstore](http://webstore.readthedocs.org/en/latest/index.html)
- **Auth**
    - Apps can pick an auth mechanism (OAuth, SAML, LDAP, etc.)
    - An app can be an auth provided. By default, a `/admin/` app can provide
      uer management functionality
    - Users have roles. Apps expose a `function(user, roles, request)` to the
      server that determines the rejection, type of rejection, error message,
      log message, etc.
    - Apps can internally further limit access based on role (e.g. only admins
      can see all rows.)
- **Uploads**
- **AJAX support** for templates



Components
--------------------------------------------------------------------------------

Layered data-driven approach

- Composable components. Apply a component over another in a layered manner
- Scaling and other transformations
- Axes
- Default stroke colour, stroke width, padding, etc
- Attribute lambda parameters
- Transformable. Transforms should also be composable.
- Ability to access template intermediate variables (layouts, scales, etc) from
  outside on server and client side
- Themes
- Any symbol instead of default symbols

Flexible rendering:

- Rendering may be on the client side or the server side
- Rendered views can be edited on the client side as well
- Renderable for PPTX, PDF, PNG, SVG, etc
- Responsive on the server side (re-layout) or the client side (preserve aspect)
- CSS classes reserved for components

Containers and controls:

- Grids
- Themes
- Standard components

Interactive charts:

- Animated transitions
- Cross-filter like filtering
- How will we incorporate dynamic interactive controls?
- Interactivity involves 3 things (We don't have a catalogue of any of these):
    1. Events / components (brushing, clicking, sliding, etc)
    2. Actions (filter, zoom-in, etc)
    3. Combinations (click-to-filter, etc)

Intelligence:

- Automated colour contrast
- Automated placement of legends
- Automated placement of labels
- Automated placement of annotations
- Text wrapping and fitting


Others
--------------------------------------------------------------------------------

- Sample datasets
- App store for apps and data

Contributing
--------------------------------------------------------------------------------

- To **suggest a feature** or **ask a question**, raise an
  [issue](http://code.gramener.com/s.anand/gramex/issues).
- To **comment on a line**, find the
  [commit](http://code.gramener.com/s.anand/gramex/blame/master/README.md) for
  the line and add a comment.
- To **follow changes**, ask @s.anand to add you as a reporter to this project.
- For anything else, raise an
  [issue](http://code.gramener.com/s.anand/gramex/issues).

Thoughts
--------------------------------------------------------------------------------
- How will be incorporate PowerPoint Smart-Art-like infographic layouts?
  - Can we make these infographics without any coding? Bret Victor like?
  - Concepts:
    - Layouts (pack in a shape, grow from a point, stack in a grid)
    - Renderings (shape, photo, size/color/other attributes)
    - Narratives
- How will we incorporate autolysis?
- Voice / video rendering

Discussion notes
--------------------------------------------------------------------------------

- **Will we have multiple instances of Gramex sharing the same memory?** No.
  This is difficult to implement in Python. Intsead, it will be delegated to
  external engines (databases, Spark, etc.)
- **Will we shift to PyPy?** No. Most libraries (such as database drivers, lxml,
  etc.) do not yet work on PyPy.
