---
title: CaptureHandler tutorial
...

[TOC]

`CaptureHandler` allows you to take screenshot of pages.
It relies on Chrome's puppeteer (requires `node 9.X`) and ensure `node` is in your path.
It can be configured in `gramex` as below:

```yaml
capture:
  pattern: /$YAMLURL/capture
  handler: CaptureHandler
  kwargs:
    engine: chrome  # engine
    timeout: 10     # default request timeout for capturing
    port: 9900      # default port number
```

Configure `CaptureHandler` in front-end (or) To encode URL using `JavaScript`:

```javascript
var url = g1.url.parse(location.href); // fetch current url using g1 library
// trigger the screenshot
var capture_url = url.join('capture')
  .update({'url': location.href, 'exp': 'pdf', 'delay': 10000, 'd': 'true'})
window.open(capture_url.toString())
// or 
$('.custom-pdf').attr('href', capture_url.toString())
```

To encode URLs using a `python` template:

```javascript
{% from six.moves.urllib_parse import urlencode %}
<a href="capture?{{ urlencode(url='...', header='header text') }}"
```

## Schedule CaptureHandler

`CaptureHandler` can be used as a service via `python`. YAML configuration for which is as follows:

```yaml
capture-scheduler:
  function: app.screenshot_scheduler
  dates: '-'
  hours: '2'	  # 2nd hour of the day
  minutes: '30' # 30th minute
```

corresponding `screenshot_scheduler` function in `app.py`:

```python
def screenshot_scheduler():
    params = {'url': 'https://learn.gramener.com/guide/', 'delay': 4000, 'ext': 'png'}
    url = 'http://127.0.0.1:8001/capture/?' + urlencode(params)
    webbrowser.open(url)
```

## Supported Arguments

Arguments supported by `CaptureHandler`:

- `?url=` url of the page to capture e.g: `?url=http://www.gramener.com`
- `?file=` captured file name e.g: `?file=capture1`
- `?delay=` delay for page capturing (Note:  delay should be less than timeout) in milliseconds e.g: `?delay=10000`
    (or) `?delay=renderComplete` waits until the javascript loads
- `?ext=` capturing format like `png`/`jpg`/`pdf`/`pptx` (Note: `pptx` only in chrome v1.23.1)

For `PDF`:

  - `?format=` PDF formats like A0, A1, A2, A3, A4, Legal, Letter or Tabloid. Default: A4
  - `?orientation=`  portrait / landscape. Default: potrait
  - `?title=` to add page footer (optional)
  - `?media=` print / screen , Default: screen for chrome engine

For `PNG`/`JPG`:

  - `?width=` Image width, Default: `1200`
  - `?height=` Image height, Default: auto (full page)
  - `?selector=` restrict screenshot of the page using css selector (optional)

For `PPTX`:

  - `?layout=` A3, A4, Letter, `16x9`, `16x10`, `4x3`. Default: `4x3`
  - `?dpi=` image resolution (dots per inch). Default: `96` (optional)
  - `?width=` viewport width in pixels (optional)
  - `?height=` height to clip output to. Leave it blank for full page height (optional)
  - `?selector=` restrict screenshot of the page using css selector
  - `?title=` title slide (optional)
  - `?title_size=` font size in points (optional)
  - `?x=` x position in px, ie., left-margin
  - `?y=` y position in px, ie., lefttop-margin

For detailed documentation, visit [CaptureHandler](../capturehandler/).
