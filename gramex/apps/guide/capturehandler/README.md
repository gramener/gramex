title: Gramex takes screenshots

[CaptureHandler](capturehandler) takes screenshots of pages using either
[Chrome][puppeteer] or
[PhantomJS](http://phantomjs.org/).

[puppeteer]: https://github.com/GoogleChrome/puppeteer/

[TOC]

## Chrome

**Chrome is the recommended engine from v1.23**. To set it up:

- Install [Node 8.x](https://nodejs.org/en/) -- earlier versions won't work.
  Ensure that `node` is in your PATH.
- Uninstall and [re-install Gramex](../install/) (or run `gramex install capture` instead.)

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

By default, requests timeout within 10 seconds. To change this, use `timeout:`.

    :::yaml
            pattern: /$YAMLURL/capture
            handler: CaptureHandler
            kwargs:
                timeout: 20     # Wait for max 20 seconds for server to respond

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

## PhantomJS

[PhantomJS](http://phantomjs.org/) is **out-dated** but is the default for
backward compatibility. To use it, install [PhantomJS](http://phantomjs.org/) and
it to your PATH. Then add this to `gramex.yaml`:

    :::yaml
    url:
        capture:
            pattern: /$YAMLURL/capture
            handler: CaptureHandler

Note that the `engine: phantomjs` is not required.

## Screenshot service

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
  <br>**Example**: [?url=https://example.org/](capture?url=https://example.org/)
- `?file=`: screenshot file name. Defaults to `screenshot`.
  <br>**Example**: [?file=newfile](capture?file=newfile)
- `?ext=`: format of output. Can be pdf, png or jpg. Defaults to `pdf`.
  <br>**Example**: [?ext=png](capture?ext=png)
- `?delay=`: milliseconds to wait for before taking a screenshot. This value must
  be less than the `timeout:` set in the `kwargs:` section.
  <br>**Example**: [?delay=1000](capture?url=timer.html&delay=1000)
  captures this [timer page](timer.html) with a ~1000 ms delay
- For PDF:
    - `?format=`: A3, A4, A5, Legal, Letter or Tabloid. Defaults to A4.
      <br>**Example**: [?format=Tabloid](capture?format=Tabloid)
    - `?orientation=`: portrait or landscape. Defaults to portrait.
      <br>**Example**: [?orientation=landscape](capture?orientation=landscape)
    - `?title=`: footer for the page. To be implemented
    - `media=`: `print` or `screen`. Defaults to `screen`. Only for Chrome.
      <br>**Example**: [?media=print](capture?media=print)
- For images (PNG/JPG):
    - `?width=`: image output width. Default: 1200
      <br>**Example**: [?width=600](capture?width=600&ext=png)
    - `?height=`: image output height. Default: auto (full page)
      <br>**Example**: [?height=600](capture?height=600&ext=png)
    - `?selector=`: Restrict screenshot to (optional) CSS selector in URL
      <br>**Example**: [?selector=.content](capture?selector=.content&ext=png) excludes the sidebar
    - `?scale=`: zooms the screen by a factor. Defaults to 1.
      <br>**Example**: [?scale=0.2](capture?scale=0.2&ext=pdf) compared with
      [?scale=1](capture?scale=1&ext=pdf)
- `?debug=`: displays request / response log requests on the console.
    - `?debug=1` logs all responses and HTTP codes. It also logs browser
      console.log messages on the Gramex console
    - `?debug=2` additionally logs all requests

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

## Screenshot library

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
