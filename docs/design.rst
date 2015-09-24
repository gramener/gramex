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

1. A :doc:`server` that provides core services (URL handling, authentication,
   logging, etc.) to the entire web server.
2. :doc:`handlers` that respond to HTTP requests. They may show templates, act
   as a websocket, provide a data interface, serve static files, etc.
3. :doc:`components` that render content of different kinds (charts, tables,
   UI components, etc.)
