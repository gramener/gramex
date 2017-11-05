A library to download web pages as PDF or image using
[Chrome](https://github.com/GoogleChrome/puppeteer/) or
[PhantomJS](http://phantomjs.org/) as the engine.

## Chrome

On Linux, run this **as root**:

    # Install node.js 8.x or above -- this is required
    curl -sL https://deb.nodesource.com/setup_8.x | bash -
    apt-get install -y nodejs
    # Install dependencies. Some may already exist. No harm re-installing
    apt-get install -y libpangocairo-1.0-0 libx11-xcb1 libxcomposite1 libxdamage1 libxi6 libxtst6 \
            libnss3 libcups2 libxss1 libxrandr2 libgconf2-4 libasound2 libatk1.0-0 libgtk-3-0
    # Install puppeteer
    npm install puppeteer

On Windows, run:

    npm install puppeteer

The commands below run `chromecapture.js` as a web server on port 8080. (You can
change `--port=8080` to any other port.)

    node chromecapture.js
    node chromecapture.js --port=8080

Now, visit http://localhost:8080/?url=http://gramener.com&file=gramener.pdf

On the command line:

    node chromecapture.js --url=https://gramener.com/ --ext=pdf --file=gramener

This saves <https://gramener.com/> as `gramener.pdf`

## PhantomJS

On Linux, run:

    sudo apt-get install phantomjs

On Windows, download and install [PhantomJS 2.1.1](https://bitbucket.org/ariya/phantomjs/downloads/).

The commands below run `capture.js` as a web server on port 8080. (You can change
`--port=8080` to any other port.)

    phantomjs --ssl-protocol=any capture.js
    phantomjs --ssl-protocol=any capture.js --port=8080

Now, visit http://localhost:8080/?url=http://gramener.com&file=gramener.pdf

On the command line:

    phantomjs --ssl-protocol=any capture.js --url=https://gramener.com/ --ext=pdf --file=gramener

This saves <https://gramener.com/> as `gramener.pdf`

## Parameters

All parameters below are applicable both for the command line as well as the
web server.

- `url=`: required -- the URL to be downloaded as a PDF or an image.
- `file=`: sets the base name of the download file. Defaults to screenshot
- `ext=`: sets the extension. Supported extensions: .pdf (default), .png, .jpg
- `delay=`: milliseconds to wait before screenshot (for dynamic javascript)
- `cookie=`: optional `cookie` to pass to `url`. The `Cookie: ` HTTP header can also be used
- `scale=`: 2 doubles the resolution, .5 halves it
- PDF options:
    - `format=`: `A3`, `A4` (default), `A5`, `Legal`, `Letter`, `Tabloid`
    - `orientation=`: `landscape` for landscape, `portrait` is default
    - `title=`: Footer title. Headers and footers can be modified in `margin.js`
    - `media=`: `print` or `screen`. Defaults to `screen`. Only for Chrome.
- Raster (PNG/JPG/GIF) options:
    - `width=`: viewport width in pixels. (Default: 1200px)
    - `height=`: optional height to clip output to. Leave it blank for full page height
    - `selector=`: CSS selector to take a screenshot of
