A [PhantomJS](http://phantomjs.org/) library to download web pages as PDF or image.

This requires [PhantomJS 2.1.1](https://bitbucket.org/ariya/phantomjs/downloads/).

## Usage

### As a web server

Both these commands run `capture.js` as a web server on port 8080. (You can
change `--port=8080` to any other port.)

    phantomjs --ssl-protocol=any capture.js
    phantomjs --ssl-protocol=any capture.js --port=8080

Now, visit http://localhost:8080/?url=http://gramener.com&file=gramener.pdf

### On the command line

    phantomjs --ssl-protocol=any capture.js --url=https://gramener.com/ --ext=pdf --file=gramener

This saves <https://gramener.com/> as `gramener.pdf`

## List of parameters

All parameters below are applicable both for the command line as well as the
web server.

- `url=`: required -- the URL to be downloaded as a PDF or an image
- `file=`: sets the base name of the download file. Defaults to screenshot
- `ext=`: sets the extension. Supported extensions: .pdf (default), .png, .jpg
- `delay=`: milliseconds to wait before screenshot (for dynamic javascript)
- `cookie=`: optional `cookie` to pass to `url`. The `Cookie: ` HTTP header can also be used
- `scale=`: 2 doubles the resolution, .5 halves it
- PDF options:
    - `format=`: `A3`, `A4` (default), `A5`, `Legal`, `Letter`, `Tabloid`
    - `orientation=`: `landscape` for landscape, `portrait` is default
    - `title=`: Footer title. Headers and footers can be modified in `margin.js`
- Raster (PNG/JPG/GIF) options:
    - `width=`: viewport width in pixels. (Default: 1200px)
    - `height=`: optional height to clip output to. Leave it blank for full page height
    - `selector=`: CSS selector to take a screenshot of

## Deployment

To install PhantomJS on Linux, run:

    sudo apt-get install phantomjs

On Windows, download and install [PhantomJS 2.1.1](https://bitbucket.org/ariya/phantomjs/downloads/).
