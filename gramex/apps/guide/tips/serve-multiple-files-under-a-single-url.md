---
title: Serving multiple files under a single URL
prefix: Tip
...

`FileHandler` can serve multiple files under a single URL.

For example, if you use `jQuery`, `Bootstrap` and `D3` in your project, you can create a single URL called `libraries.js` that concatenates all of these files into one. See example:

    :::yaml
    pattern: /$YAMLURL/libraries.js
    handler: FileHandler
    kwargs:
        path:
            - $YAMLPATH/bower_components/jquery/dist/jquery.min.js
            - $YAMLPATH/bower_components/bootstrap/dist/bootstrap.min.js
            - $YAMLPATH/bower_components/d3/d3.min.js
        headers:
            Content-Type: application/json

This is also try of CSS files, CSV files, and any other file formats that can be concatenated.
