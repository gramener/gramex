Design
======

Gramex 1.0 is the new backward-incompatible re-boot of Gramener's visualisation
platform.

What's new?
    Gramex 1.0 will not require programming knowledge. It will be driven
    initially by configurations, and then by GUI, to construct visuals.
    (Programmatic extension will be *possible*, not required.)

Why 1.0?
    We use semantic versioning. ``1.0`` means we have a published API that we
    follow.

Why backward-incompatible?
    There are many bad practices that Gramex 0.x encourages that we want to
    break-away from. For example, inconsistent attributes in chart components.

Principles
----------

1. **Data, not code** Apps are written as declarative configurations, not code.
   We use **YAML** for configurations. (XML is verbose, JSON lacks comments and
   references.) These configurations are reloaded transparently.
2. **Modular**. Every part is a module, usable independent of Gramex. These
   components may also be licensed independently.
3. **Web rendering**. All views are rendered via HTML/CSS/JS, not Python. We
   support IE11, Edge, Chrome, Firefox, mobile Safari. (From Jan 12 2016, `IE10
   won't be supported`_.)

.. _IE10 won't be supported: https://support.microsoft.com/en-us/gp/microsoft-internet-explorer

These are proposed principles, for discussion.

1. **Lazy computations**. Defer computation to as late as possible.
2. **Asynchronous**. I/O does not block the CPU.

Architecture
------------

Gramex has:

1. A server that provides core services (URL handling, authentication, logging,
   etc.) to the entire web server.
2. Handlers that respond to HTTP requests. They may show templates, act as a
   websocket, provide a data interface, serve static files, etc.
3. Components that render content of different kinds (charts, tables, UI
   components, etc.)

Decisions
---------

URL patterns must be explicit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Gramex 0.x allowed URLs to be **rebased**. For example, if an app is deployed at
`/` it can be served at `/app/` with URLs automatically getting corrected.

This requires the application to consistently use ``rebase_uri`` and the front-
end proxy to send an ``X-Request-URI`` header. Using ``rebase_uri`` is no longer
possible with views being generated on the front-end. ``X-Request-URI`` needs a
front-end proxy like nginx, which can be difficult to configure.

So we prefer simplicity over functionality and disallow rebasing.

Henceforth, apps must know their exact (final) URL.

Use HTML5 web components to build templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We need a *simple* mechanism to construct and extend templates.

One possibility is to use YAML or JSON to generate HTML and build a GUI around
it. But:

  - There's no simple data structure to represent inline statements like "abc
    <i>italics</i> def" and multi-keys like "<br><br>".
  - There's no simple extension mechanism to modify attributes and nodes

Instead, we can use HTML itself as the language. Tooling support is limited but
growing.

Use Python as the HTTP server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Data processing needs to happen in Python in any case. The library ecosystem is
much richer here. The ecosystem for enterprise auth and database connectivity is
also richer.

What Node does better than Python is rendering pages on the server side. This
may not be required in every project. When required, we can integrate with Node.

So, Gramex 1.0 will be a Python server with Python-based HTML processing.
