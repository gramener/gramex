title: Gramex takes screenshots

[CaptureHandler](capturehandler) takes screenshots of pages using either
[Chrome][puppeteer] or
[PhantomJS](http://phantomjs.org/).

[puppeteer]: https://github.com/GoogleChrome/puppeteer/

[PhantomJS](http://phantomjs.org/) is the default for backward compatibility, but
it is out-dated. To use it, install [PhantomJS](http://phantomjs.org/) and it to
your PATH. Then add this to `gramex.yaml`:

    :::yaml
    url:
        capture:
            pattern: /$YAMLURL/capture
            handler: CaptureHandler

**Chrome is the recommended engine from v1.23**.

- Install [Node 8.x](https://nodejs.org/en/) -- earlier versions won't work.
  Ensure that `node` is in your PATH.
- Uninstall and [re-install Gramex](../install/). (Or run `npm install` from
  `apps/capture/` under where Gramex is installed.)

Add this to `gramex.yaml`:

    :::yaml
    url:
        capture:
            pattern: /$YAMLURL/capture
            handler: CaptureHandler
            kwargs:
                engine: chrome

When Gramex runs, it starts `node chromecapture.js --port 9900` running a
node.js based web application (chromecapture.js) at port 9900.

To change the port, use:

    :::yaml
            pattern: /$YAMLURL/capture
            handler: CaptureHandler
            kwargs:
                engine: chrome
                port: 9901              # Use a different port

To use an existing instance of chromecapture.js running on a different port, use:

    :::yaml
            pattern: /$YAMLURL/capture
            handler: CaptureHandler
            kwargs:
                engine: chrome
                url: http://server:port/capture/    # Use chromecapture.js from this URL

The default chromecapture.js is at `$GRAMEXPATH/apps/capture/chromecapture.js`.
To use your own chromecapture.js, run it using `cmd:` on any port and point
`url:` to that port:

    :::yaml
            pattern: /$YAMLURL/capture
            handler: CaptureHandler
            kwargs:
                engine: chrome
                cmd: node /path/to/chromecapture.js --port=9902
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
    <a href="capture?ext=jpg">JPG screenshot</a>

Try it here:

- [PDF screenshot](capture?ext=pdf)
- [PNG screenshot](capture?ext=png)
- [JPEG screenshot](capture?ext=jpg)

It accepts the following arguments:

- `?url=`: URL to take a screenshot of. This defaults to `Referer` header. So if
  you link to a `capture` page, the source page is generally used.
- `?file=`: screenshot file name. Defaults to `screenshot`
- `?ext=`: format of output. Can be pdf, png or jpg
- `?delay=`: milliseconds to wait for before taking a screenshot. This value must
  be less than the `timeout:` set in the `kwargs:` section
- `?scale=`: zooms the screen by a factor
- For PDF:
    - `?format=`: A3, A4, A5, Legal, Letter or Tabloid. Defaults to A4
    - `?orientation=`: portrait or landscape. Defaults to portrait
    - `?title=`: footer for the page
    - `media=`: `print` or `screen`. Defaults to `screen`. Only for Chrome.
- For images (PNG/JPG):
    - `?width=`: screen width. Default: 1200
    - `?height=`: screen height. Default: 768
    - `?selector=`: Restrict screenshot to (optional) CSS selector in URL
- `?debug=`: displays request / response log requests on the console.
    - `?debug=1` logs all responses and HTTP codes. It also logs browser
      console.log messages on the Gramex console
    - `?debug=2` additionally logs all requests

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
    capture = Capture(engine='chrome')          # This runs chromecapture.js at port 9900
    url = 'https://gramener.com/demo/'          # Page to take a screenshot of
    with open('screenshot.pdf', 'wb') as f:
        f.write(capture.pdf(url, orientation='landscape'))
    with open('screenshot.png', 'wb') as f:
        f.write(capture.png(url, width=1200, height=600, scale=0.8))

The [Capture](capture) class has convenience methods called `.pdf()`, `.png()`,
`.jpg()` that accept the same parameters as the
[handler](screenshot-service).


[capturehandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.CaptureHandler
[capture]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.Capture
