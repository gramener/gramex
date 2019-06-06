---
title: CaptureHandler takes screenshots
prefix: CaptureHandler
...

[CaptureHandler][capturehandler] takes screenshots of pages using either
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

```yaml
url:
    capture:
        pattern: /$YAMLURL/capture
        handler: CaptureHandler
        kwargs:
            engine: chrome
```

When Gramex runs, it starts `node chromecapture.js --port 9900` running a
node.js based web application (chromecapture.js) at port 9900.

To change the port, use:

```yaml
    pattern: /$YAMLURL/capture
    handler: CaptureHandler
    kwargs:
        engine: chrome
        port: 9901              # Use a different port
```

To use an existing instance of chromecapture.js running on a different port, use:

```yaml
    pattern: /$YAMLURL/capture
    handler: CaptureHandler
    kwargs:
        engine: chrome
        url: http://server:port/capture/    # Use chromecapture.js from this URL
```

The default viewport size is 1200x768. To set a custom viewport for images or
PPTX, use `?width=` and `?height=`. For example, `?width=1920&height=1080`
changes the viewport to 1920x1080.

By default, requests timeout within 10 seconds. To change this, use `timeout:`.

```yaml
    pattern: /$YAMLURL/capture
    handler: CaptureHandler
    kwargs:
        timeout: 20     # Wait for max 20 seconds for server to respond
```

The default chromecapture.js is at `$GRAMEXPATH/apps/capture/chromecapture.js`.
To use your own chromecapture.js, run it using `cmd:` on any port and point
`url:` to that port:

```yaml
    pattern: /$YAMLURL/capture
    handler: CaptureHandler
    kwargs:
        engine: chrome
        cmd: node /path/to/chromecapture.js --port=9902
        url: http://localhost:9902/
```

To use a HTTP proxy, set the `ALL_PROXY` environment variable. If your proxy IP
is `10.20.30.40` on port `8000`, then set `ALL_PROXY` to `10.20.30.40:8000`. See
[how to set environment variables](https://superuser.com/a/284351). (You can
also use the `HTTPS_PROXY` or `HTTP_PROXY` environment variables. These
supercede `ALL_PROXY`.)

## PhantomJS

[PhantomJS](http://phantomjs.org/) is **out-dated** but is the default for
backward compatibility. To use it, install [PhantomJS](http://phantomjs.org/) and
it to your PATH. Then add this to `gramex.yaml`:

```yaml
url:
    capture:
        pattern: /$YAMLURL/capture
        handler: CaptureHandler
```

Note that the `engine: phantomjs` is not required.

## Screenshot service

You can add a link from any page to the `capture` page to take a screenshot.

```html
<a href="capture?ext=pdf">PDF screenshot</a>
<a href="capture?ext=png">PNG screenshot</a>
<a href="capture?ext=jpg">JPG screenshot</a>
<a href="capture?ext=pptx">PPTX screenshot</a>
```

Try it here:

- [PDF screenshot](capture?ext=pdf)
- [PNG screenshot](capture?ext=png)
- [JPEG screenshot](capture?ext=jpg)
- [PPTX screenshot](capture?ext=pptx)

It accepts the following arguments:

- `?url=`: URL to take a screenshot of. This defaults to `Referer` header. So if
  you link to a `capture` page, the source page is generally used.
  <br>**Example**: [?url=https://example.org/](capture?url=https://example.org/)
- `?file=`: screenshot file name. Default: `screenshot`.
  <br>**Example**: [?file=newfile](capture?file=newfile)
- `?ext=`: format of output. Can be pdf, png, jpg or pptx. Default: `pdf`.
  <br>**Example**: [?ext=png](capture?ext=png). (`ext=pptx` available only in `engine: chrome` from **v1.23.1**)
- `?delay=`: wait for before taking a screenshot.
  - If this is a number, waits for this many milliseconds.
    <br>**Example**: [?delay=1000](capture?url=timer.html&delay=1000)
    captures this [timer page](timer.html) with a ~1000 ms delay
  - If `?delay=renderComplete`, waits until the JavaScript variable
    `window.renderComplete` is set to true - or
    [30 seconds](https://github.com/GoogleChrome/puppeteer/blob/master/docs/api.md#pagewaitforfunctionpagefunction-options-args).
  - If the delay is more than the `timeout:` in the `kwargs:` section, the page
    will time out.
- For PDF:
    - `?format=`: A3, A4, A5, Legal, Letter or Tabloid. Default: A4.
      <br>**Example**: [?format=Tabloid](capture?format=Tabloid)
    - `?orientation=`: portrait or landscape. Default: portrait.
      <br>**Example**: [?orientation=landscape](capture?orientation=landscape)
    - `media=`: `print` or `screen`. Default: `screen`. (Only in `engine: chrome`)
      <br>**Example**: [?media=print](capture?media=print)
    - `header=`: a pipe-separated string that sets the page header.
      You can use `$pageNumber`, `$totalPages`, `$date`, `$title`, `$url` as variables.
      <br>**Example**: [?header=Gramener](capture?header=Gramener): Left header "Gramener"
      <br>**Example**: [?header=|$title|](capture?header=|$title|): Center header with page title
      <br>**Example**: [?header=|$pageNumber](capture?header=|$pageNumber): Right header with page number
      <br>**Example**: [?header=©|Gramener|$pageNumber/$totalPages](capture?header=©|Gramener|$pageNumber/$totalPages): Left, middle right headers.
    - `footer=`: similar to `header`
    - `headerTemplate=`: HTML template to add a custom header.
      Template cannot load external sources or run javascript, but can use inline css styles.
      [See docs](https://github.com/GoogleChrome/puppeteer/blob/master/docs/api.md#pagepdfoptions).
      Ensure that enough margin is provided for the header.
      <br>**Example**: [`?headerTemplate=<div style="border-bottom:1px solid black;display:flex;justify-content:space-between;width:100%"><span class="url"></span><span class="date"></span></div>`](capture?headerTemplate=<div style="border-bottom:1px solid black%3Bdisplay:flex%3Bjustify-content:space-between%3Bwidth:100%25"><span class="url"></span><span class="date"></span></div>)
    - `footerTemplate=`: similar to `headerTemplate`
    - `margins=`: comma-separated list of margins specifying top, right, bottom, left margins respectively.
      default margin is `1cm,1cm,1cm,1cm`.
      <br>**Example** [?margins=2cm,,2cm,](capture?margins=2cm,,2cm,) sets top and bottom margin to 2cm
- For images (PNG/JPG):
    - `?width=`: image output width. Default: 1200
      <br>**Example**: [?width=600](capture?width=600&ext=png)
    - `?height=`: image output height. Default: auto (full page)
      <br>**Example**: [?height=600](capture?height=600&ext=png)
    - `?scale=`: zooms the screen by a factor. Default: 1.
      <br>**Example**: [?scale=0.2](capture?scale=0.2&ext=png) compared with
      [?scale=1](capture?scale=1&ext=png)
    - `?selector=`: Restrict screenshot to (optional) CSS selector in URL
      <br>**Example**: [?selector=.content](capture?selector=.content&ext=png) excludes the sidebar.
    - `?emulate=`: emulate full page on a device. Ignores `?width=`, `?height=` and `?scale=`. (Only in `engine: chrome` from **v1.56.0**)
      <br>**Example**: [?emulate=iPhone 6](capture?emulate=iPhone 6&ext=png).
      Device names can be [iPhone 8, Nexus 10, Galaxy S5, etc][mobiledevices].
- For PPTX (Only in `engine: chrome` from **v1.23.1**):
    - `?layout=`: A3, A4, Letter, 16x9, 16x10, 4x3. Default: `4x3`
      <br>**Example**: [?layout=16x9](capture?layout=16x9&ext=pptx&width=1200&height=600)
    - `?dpi=`: optional image resolution (dots per inch). Default: 96
      <br>**Example**: [?dpi=192](capture?dpi=192&ext=pptx&width=1200&height=900)
    - `?width=`: optional viewport width in pixels. (Default: 1200px)
      <br>**Example**: [?width=600&height=400](capture?width=600&height=400&ext=pptx)
    - `?height=`: optional height to clip output to. Leave it blank for full page height
      <br>**Example**: [?width=1200&height=900](capture?width=1200&height=900&ext=pptx)
    - `?selector=`: CSS selector to take a screenshot of
      <br>**Example**: [?selector=.codehilite](capture?selector=.codehilite&ext=pptx)
    - `?title=`: optional slide title
      <br>**Example**: [?title=First+example&selector=.codehilite](capture?title=First+example&selector=.codehilite&ext=pptx)
    - `?title_size=`: optional title font size in points. Defaults to 18pt
      <br>**Example**: [?title=First+example&title_size=24&selector=.codehilite](capture?title=First+example&title_size=24&selector=.codehilite&ext=pptx)
    - `?x=`: optional x-position (left margin) in px. Centers by default
      <br>**Example**: [?x=10&selector=.codehilite](capture?x=10&selector=.codehilite&ext=pptx)
    - `?y=`: optional y-position (leftop margin) in px. Centers by default
      <br>**Example**: [?y=200&selector=.codehilite](capture?y=200&selector=.codehilite&ext=pptx)
    - For multiple slides, repeat `?selector=`, optionally with `?title=`, `?title_size=`, `?x=`, `?y=`, `?dpi=`.
      <br>**Example**: [?selector=.toc&title=TOC&selector=.codehilite&title=Example](capture?selector=.toc&title=TOC&selector=.codehilite&title=Example&ext=pptx)
- `?debug=`: displays request / response log requests on the console.
    - `?debug=1` logs all responses and HTTP codes. It also logs browser
      console.log messages on the Gramex console
    - `?debug=2` additionally logs all requests

When constructing the `?url=`, `?selector=`, `?title=` or any other parameter,
ensure that the URL is encoded. So a selector `#item` does not become
`?id=#item` -- which makes it a URL hash -- and instead becomes `?id=%23item`.

To encode URLs using a Python template:

```html
{% from six.moves.urllib_parse import urlencode %}
<a href="capture?{{ urlencode(url='...', header='header text') }}
```

To encode URLs using JavaScript:

```js
$('.screenshot').attr('href', 'capture' +
    '?url=' + encodeURIComponent(url) +
    '&header=' + encodeURIComponent(header))
// Or use this:
$('.some-button').on('click', function() {
    location.href = 'capture?ext=png&url=' + encodeURIComponent(url)
})
```

If the response HTTP status code is 200, the response is the screenshot.
If the status code is 40x or 50x, the response text has the error message.

**Authentication is implicit**. The cookies passed to `capture` are passed to the
`?url=` parameter. This is exactly as-if the user clicking the capture link were
visiting the target page.

To try this, [log in](../auth/simple?next=../capturehandler/) and then
[take a screenshot](capture?ext=pdf). The screenshot will show the same
authentication information as you see below.

<iframe class="w-100" frameborder="0" src="../auth/session"></iframe>

You can override the user by explicitly passing a cookie string using `?cookie=`.

**All HTTP headers are passed through** by default. CaptureHandler sends them to
Chrome (not PhantomJS), which passes it on to the target URL.

If `capture.js` was not started, or it terminated, you can restart it by adding
`?start` to the URL. It is safe to add `?start` even if the server is running. It
restarts `capture.js` only if required.

## Screenshot library

You can take screenshots from any Python program, using Gramex as a library.

```python
import logging                              # Optional: Enable logging...
logging.basicConfig(level=logging.INFO)     # ... to see messages from Capture
from gramex.handlers import Capture         # Import the capture library
capture = Capture(engine='chrome')          # This runs chromecapture.js at port 9900
url = 'https://gramener.com/demo/'          # Page to take a screenshot of
with open('screenshot.pdf', 'wb') as f:
    f.write(capture.pdf(url, orientation='landscape'))
with open('screenshot.png', 'wb') as f:
    f.write(capture.png(url, width=1200, height=600, scale=0.8))
```

The [Capture](capture) class has convenience methods called `.pdf()`, `.png()`,
`.jpg()` that accept the same parameters as the
[handler](#screenshot-service).


[capturehandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.CaptureHandler
[capture]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.Capture
[mobiledevices]: https://github.com/GoogleChrome/puppeteer/blob/v1.17.0/lib/DeviceDescriptors.js
