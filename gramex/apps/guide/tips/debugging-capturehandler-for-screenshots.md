---
title: Debugging CaptureHandler for screenshots
prefix: Tip
...

CaptureHandler has an option to debug at PhantomJS level. This is documented in the [guide for CaptureHandler](../capturehandler/#screenshot-service).

While sending the request, you can mention a debug flag as below

    :::yaml
    /capture?debug=2&delay=3000&url=...

- `?debug=1` logs all responses, HTTP codes along with console.log messages
- `?debug=2` logs the above + all HTTP requests

## Other notes

1. A 3 second difference between the request delay and timeout argument for CaptureHandler is a working recommendation. For instance, in JS request the delay can be 8000 (milliseconds) depending on your dashboard and timeout in CaptureHandler (default is 10 seconds) can be 11 (kwargs section in YAML)
2. ES6 isn't supported in PhantomJS. Please be mindful of this while debugging
