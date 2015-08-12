Gramex 1.0
================================================================================

Gramex 1.0 is a backward-incompatible re-boot of the visualisation platform.
This is the work-in-progress design for Gramex 1.0. It is based on our learnings
and needs.

Gramex 1.0 is more modular. Many of its parts can be used independently. It can
use third party modules easily.

It has 3 parts: the server, services, and components.

Server
--------------------------------------------------------------------------------

The server is the core I/O engine: it translates requests into responses.

- **Namespaced app folders**.
    - Add a directory `app/`, and the URL mappings for `/app/...` will be taken
      from the `app/` directory.
    - With `/app/` there is full flexibility on how to handle the URLs
    - No URLs outside `/app/` will be affected.
    - Configurations use data, not code. (e.g. YAML, not Python)
- **Moderl protocols** are supported out of box.
    - HTTP, by default
    - HTTPS native support
    - Websocket
    - HTTP/2.0 a.k.a. SPDY
- **Asynchronous**
    - Executes on an event loop. **Apps can be async** on this loop.
    - New loops on **threads** are possible.
    - Responses can be interrupted, even without the consent of the app. (If the
      connection closes, just kill the function.)
- **Security**
    - Apps can pick an auth mechanism (OAuth, SAML, LDAP, etc.)
    - An app can be an auth provided. By default, a `/admin/` app can provide
      uer management functionality
    - Users have roles. Apps expose a `function(user, roles, request)` to the
      server that determines the rejection, type of rejection, error message,
      log message, etc.
    - Apps can internally further limit access based on role (e.g. only admins
      can see all rows.)
- **Caching**
    - Output follows HTTP caching policy. Server acts as a caching HTTP proxy.
- **Logging** mechanism common across apps
    - Single global logger, modified to accept `app` as a parameter
    - Configured to store / transmit logs as and how required

Externals:

- **Distributed computing** is handled by the apps themselves. This can be via
  an external computing engine (e.g. Spark) or one that is custom-built.
- **Load balancing** is handled by a front-end balancer (e.g. nginx).

References:

- [Ben Darnell's template plans for Tornado 4.1](https://groups.google.com/forum/?fromgroups#!searchin/python-tornado/template$20asynchronous%7Csort:date/python-tornado/Eoyb2wphJ-o/fj9EAb166PIJ)
- [`asynchronous` directive pull request](https://github.com/tornadoweb/tornado/pull/553)
- [`coroutine=` parameter pull request](https://github.com/tornadoweb/tornado/pull/1311)


Services
--------------------------------------------------------------------------------

Services are offered to all apps, which may expose them with or without changes.

- **Rendering** components to PDF, PPTX, PNG, SVG, etc.
- **Caching**. Any structure can be cached and re-used across apps.
- **Computation workflow**.


Components
--------------------------------------------------------------------------------

- Grammar of Graphics
- Consistent rendering principles
- Scaling and other transformations
- Axes
- Colour contrast
- Default stroke colour, stroke width, padding, etc
- Attribute lambda parameters
- Transformable. Transforms should also be composable.
- Ability to access template intermediate variables (layouts, scales, etc) from outside
- Rendering may be on the client side or the server side

Others
--------------------------------------------------------------------------------

- Provide sample datasets

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
