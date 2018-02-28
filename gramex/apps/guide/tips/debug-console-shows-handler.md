---
title: Gramex console shows handler name
prefix: Tip
...

The Gramex console now shows the name of the URL handler that handles a request.
For example:

    INFO    21-Dec 10:39:51 __init__ 200 GET /url (127.0.0.1) 2.00ms handler-name

This helps with debugging when you have multiple URLs (perhaps across YAML
files.)

For example, this handler dumps the session as JSON:

    :::yaml
    url:
      myapp/session:
        pattern: /$YAMLURL/sesion
        handler: FunctionHandler
        kwargs:
          function: json.dumps(handler.session)

But `/session` throws a 404. The Gramex console used to show this unhelpful message:

    WARNING 21-Dec 10:42:35 web 404 GET /session (127.0.0.1) 6.00ms

From Gramex 1.25, the console shows this:

    WARNING 21-Dec 10:39:48 __init__ 404 GET /session (127.0.0.1) 3.00ms default

The "default" indicates the handler name. So no handler is defined for `/session`!

Inspect the YAML above. There is a spelling error: `/sesion` instead of
`/session`. Visiting `/sesion` shows this log:

    INFO    21-Dec 10:39:51 __init__ 200 GET /sesion (127.0.0.1) 2.00ms myapp/session

The "myapp/session" shows that it's been handled by `myapp/session`.

This makes debugging easier - to find which handler actually renders the output.
