title: Gramex takes screenshots

The [CaptureHandler](capturehandler) takes screenshots of pages using PhantomJS.

First, install [PhantomJS](http://phantomjs.org/) and it to your PATH. Then add
this to `gramex.yaml`:

    :::yaml
    url:
        capture:
            pattern: /$YAMLURL/capture
            handler: CaptureHandler

When Gramex runs, it starts `phantomjs capture.js --port 9900` running a
PhantomJS based web application (capture.js) at port 9900.

To change the port, use:

    :::yaml
            pattern: /$YAMLURL/capture
            handler: CaptureHandler
            kwargs:
                port: 9901              # Use a different port

To use an existing instance of capture.js running on a different port, use:

    :::yaml
            pattern: /$YAMLURL/capture
            handler: CaptureHandler
            kwargs:
                url: http://server:port/capture/    # Use capture.js from this URL

The default capture.js is under `$GRAMEXPATH/apps/capture/capture.js`. To use
your own capture.js, run it using `cmd:` on any port and point `url:` to that
port:

    :::yaml
            pattern: /$YAMLURL/capture
            handler: CaptureHandler
            kwargs:
                cmd: phantomjs --ssl-protocol=any /path/to/capture.js --port=9902
                url: http://localhost:9902/

By default, requests timeout within 10 seconds. To change this, use `timeout:`.

    :::yaml
            pattern: /$YAMLURL/capture
            handler: CaptureHandler
            kwargs:
                timeout: 20     # Wait for max 20 seconds for server to respond

# Screenshot service

You can add a link from any page to the `capture` page to take a screenshot.

    :::html
    <a href="capture?ext=pdf">PDF screenshot</a>
    <a href="capture?ext=png">PNG screenshot</a>
    <a href="capture?ext=jpg">GIF screenshot</a>
    <a href="capture?ext=gif">GIF screenshot</a>

Try it here:

- [PDF screenshot](capture?ext=pdf)
- [PNG screenshot](capture?ext=png)
- [JPEG screenshot](capture?ext=jpg)
- [GIF screenshot](capture?ext=gif)

It accepts the following arguments:

- `?url=`: URL to take a screenshot of. This defaults to `Referer` header. So if
  you link to a `capture` page, the source page is generally used.
- `?file=`: screenshot file name. Defaults to `screenshot`
- `?ext=`: format of output. Can be pdf, png, gif or jpg
- `?selector=`: Restrict screenshot to (optional) CSS selector in URL
- `?delay=`: milliseconds to wait for before taking a screenshot. This value must
  be less than the `timeout:` set in the `kwargs:` section
- `?format=`: A3, A4, A5, Legal, Letter or Tabloid. Defaults to A4. For PDF
- `?orientation=`: portrait or landscape. Defaults to portrait. For PDF
- `?header=`: header for the page. For PDF
- `?footer=`: footer for the page. For PDF
- `?width=`: screen width. Default: 1200. For PNG/GIF/JPG
- `?height=`: screen height. Default: 768. For PNG/GIF/JPG
- `?scale=`: zooms the screen by a factor. For PNG/GIF/JPG
- `?debug=`: displays request / response log requests on the console. `?debug=1`
  logs all responses and HTTP codes. `?debug=2` logs all requests and responses

Here are some examples of usage:

    ?url=https://gramener.com/demo/                         # Capture gramener.com/demo/
    ?url=https://gramener.com/demo/&file=demo&ext=png       # Save as demo.png
    ?url=https://gramener.com/demo/&selector=.case-studies  # Capture only class="case-studies"
    ?url=...&delay=2000                                     # Capture after 2 seconds
    ?url=...&format=A4&orientation=landscape                # Capture as A4 landscape
    ?url=...&header=Header text&footer=Footer text          # Add header and footer text
    ?url=...&ext=png&width=1600&height=900&scale=0.9        # 1600x900 PNG, zoomed out to 90%

When constructing the `?url=`, `?header=`, `?footer=` or any other parameter,
ensure that the URL is encoded. For example, when using a Python template:

    :::html
    {% from six.moves.urllib_parse import urlencode %}
    <a href="capture?{{ urlencode(url='...', header='header text') }}

In JavaScript:

    :::js
    $('.screenshot').attr('href', 'capture' +
        '?url=' + encodeURIComponent(url) +
        '&header=' + encodeURIComponent(header))

Or:

    $('.some-button').on('click', function() {
        location.href = 'capture?ext=png&url=' + encodeURIComponent(url)
    })

**Authentication is implicit**. The cookies passed to `capture` are passed to the
`?url=` parameter. This is exactly as-if the user clicking the capture link were
visiting the target page.

To try this, [log in](../auth/simple?next=../capturehandler/) and then
[take a screenshot](capture?ext=pdf).

<iframe frameborder="0" src="../auth/session"></iframe>

You can override the user by explicitly passing a cookie string using `?cookie=`.

If `capture.js` was not started, or it terminated, you can restart it by adding
`?start` to the URL. It is safe to add `?start` even if the server is running. It
restarts `capture.js` only if required.

# Screenshot library

You can take screenshots from any Python program, using Gramex as a library.

    :::python
    import logging                              # Optional: Enable logging...
    logging.basicConfig(level=logging.INFO)     # ... to see messages from Capture
    from gramex.handlers import Capture         # Import the capture library
    capture = Capture()                         # This runs capture.js at port 9900
    url = 'https://gramener.com/demo/'          # Page to take a screenshot of
    with open('screenshot.pdf', 'wb') as f:
        f.write(capture.pdf(url, orientation='landscape'))
    with open('screenshot.png', 'wb') as f:
        f.write(capture.png(url, width=1200, height=600, scale=0.8))

The [Capture](capture) class has convenience methods called `.pdf()`, `.png()`,
`.jpg()` and `.gif()` that accept the same parameters as the
[handler](screenshot-service).


[capturehandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.CaptureHandler
[capture]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.Capture
