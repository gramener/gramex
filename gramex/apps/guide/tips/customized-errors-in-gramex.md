---
title: Customized errors in Gramex
prefix: Tip
...

You can define your own custom error handlers in Gramex.

There are 2 kinds of errors we often find. FunctionHandlers raise a `HTTP 500 (Internal Server Error)` and FileHandlers raise a `HTTP 404 (File Not Found Error)`

You can design an error page consistent with your project's design. Just create a 1HTML` file and in your `gramex.yaml` handler, include:

    :::yaml
    url:
        pattern: ...
        handler: ...
        kwargs:
            ...
            error:
                404: {path: $YAMLPATH/404.html}
                500: {path: $YAMLPATH/500.html}

Here is an example of a [custom 404 error page](../config/error-page).

The error pages are actually templates that have additional information about the error. You can choose to display this or not.

Remember: you don't need to copy-paste this on every handler. Just [re-use configurations](../config/#reusing-configurations).
