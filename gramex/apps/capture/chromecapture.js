/* eslint-env es6, node */
/* eslint-disable no-console */

const puppeteer = require('puppeteer')
const image_size = require('fast-image-size')
const bodyParser = require('body-parser')
const minimist = require('minimist')
const express = require('express')
const cookie = require('cookie')
const path = require('path')
const tmp = require('tmp')
const fs = require('fs')
const _ = require('lodash')

const default_port = 8090
const version = '1.1.0'
const server_version = 'ChromeCapture/' + version
const folder = path.dirname(path.resolve(process.argv[1]))
const homepage = path.join(folder, 'index.html')

let browser, page, app, server
let render_dir = folder             // Used by render() to save the file

const pptx_size = {
  'A3':     [14,   10.5  ],
  'A4':     [10.83, 7.5  ],
  'Letter': [11,    8.5  ],
  '16x10':  [10,    6.25 ],
  '16x9':   [10,    5.625],
  '4x3':    [10,    7.5  ]
}

// HTTP headers to chromecapture are forwarded to the URL -- except for these.
// Keep this sync-ed with the same list in capturehandler.py
// See https://en.wikipedia.org/wiki/List_of_HTTP_header_fields
const ignore_headers = [
  'host',               // The URL will determine the host
  'connection',         // Let puppeteer manage the connection
  'upgrade',            // .. and the upgrades
  'content-length',     // The new request will have a different content-length
  'content-md5',        // ... and different content-md5
]


async function screenshot(page, options, selector) {
  // If a previous clip was set, remove it
  delete options.clip
  // Apply clip based on selector
  if (selector) {
    const rect = await page.evaluate(
      function(selector) {
        let el = document.querySelector(selector)
        if (!el) return
        let rect = el.getBoundingClientRect()
        return {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
      },
      selector)
    if (!rect)
      throw new Error('No selector ' + selector)
    options.clip = rect
  }
  // Take the screenshot
  await page.screenshot(options)
}


async function render(q) {
  console.log('Opening', q.url)

  let ext = q.ext || 'pdf'
  let media = q.media || 'screen'
  let file = (q.file || 'screenshot') + '.' + ext
  let headers = q.headers || {}
  let target = path.join(render_dir, file)
  if (fs.exists(target))
    fs.unlinkSync(target)

  let args = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
  ]
  // If a proxy environment variable is defined, use it
  let proxy = process.env.HTTPS_PROXY || process.env.HTTP_PROXY || process.env.ALL_PROXY
  if (proxy)
    args.push('--proxy-server=' + proxy)

  if (typeof browser == 'undefined')
    browser = await puppeteer.launch({args: args})
  if (typeof page == 'undefined')
    page = await browser.newPage()

  // Clear past cookies
  let cookies = await page.cookies(q.url)
  await page.deleteCookie(...cookies)
  // Parse cookies and set them on the page, so that they'll be sent on any
  // requests to this URL. (This overrides the request HTTP header "Cookie")
  if (q.cookie) {
    let cookieList = []
    let cookieObj = cookie.parse(q.cookie)
    for (let key in cookieObj)
      cookieList.push({name: key, value: cookieObj[key], url: q.url})
    await page.setCookie(...cookieList)
    delete headers.cookie
  }

  // Set additional HTTP headers
  ignore_headers.forEach(function (header) { delete headers[header] })
  await page.setExtraHTTPHeaders(headers)

  await page.goto(q.url)

  if (q.delay == 'renderComplete')
    await page.waitForFunction('window.renderComplete')
  else if (!isNaN(+q.delay))
    await new Promise(res => setTimeout(res, +q.delay))

  if (ext == 'pdf') {
    // TODO: header / footer
    if (media != 'print')
      await page.emulateMedia(media)
    await page.pdf({
      path: target,
      format: q.format || 'A4',
      landscape: q.orientation == 'landscape',
      scale: q.scale || 1,
      margin: {top: '1cm', right: '1cm', bottom: '1cm', left: '1cm'},
      printBackground: true
    })
  } else {
    const viewport = {
      width: +q.width || 1200,
      height: +q.height || 768,
      deviceScaleFactor: +q.scale || 1
    }
    await page.setViewport(viewport)
    const options = {
      path: target,
      fullPage: !q.height && !q.selector  // If height and selector not specified, use full height
    }
    if (ext == 'pptx') {
      const officegen = require('officegen')
      const pptx = officegen('pptx')
      const repeat_cols = ['selector', 'title', 'title_size', 'x', 'y', 'dpi']
      // Convert to arrays
      for (let key of repeat_cols)
        if (!Array.isArray(q[key]))
          q[key] = [q[key]]
      // find length of largest array
      const max_length = _.max(_.map(repeat_cols, col => q[col].length))
      // forward fill everything with the last value to ensure equal length
      repeat_cols.forEach(col => {
        let last_val = q[col][q[col].length - 1]
        for (let i=q[col].length; i<max_length; i++)
          q[col].push(last_val)
      })
      const image_files = []
      let pages = _.zip(q.selector, q.title, q.title_size, q.x, q.y, q.dpi).entries()
      for (const [index, [selector, title, title_size, x, y, dpi]] of pages) {
        options.path = target.replace(/\.pptx$/, '.' + index + '.png')
        image_files.push(options.path)
        await screenshot(page, options, selector)
        const fmt = pptx_size[q.layout in pptx_size ? q.layout : '4x3']
        // 72 points = 1 inch
        pptx.setSlideSize(fmt[0] * 72, fmt[1] * 72)
        const scale = 72 / (+dpi || 96)
        const slide = pptx.makeNewSlide()
        const size = image_size(options.path)
        slide.addImage(options.path, {
          x: typeof x == 'undefined' ? 'c' : x * scale,
          y: typeof y == 'undefined' ? 'c' : y * scale,
          cx: size.width * scale,
          cy: size.height * scale
        })
        if (typeof title != 'undefined')
          slide.addText(title, {x: 0, y: 0, cx: '100%', font_size: +title_size || 18})
      }
      await new Promise(res => {
        const out = fs.createWriteStream(target)
        pptx.generate(out)
        out.on('close', res)
      })
      image_files.forEach(path => fs.unlinkSync(path))
    } else {
      await screenshot(page, options, q.selector)
    }
  }
  return {path: target, file: file}
}

function webapp(req, res) {
  let q = Object.assign({}, req.query, req.body)
  if (!q.url)
    return res.sendFile(homepage)
  q.cookie = q.cookie || req.headers.cookie
  q.headers = req.headers
  render(q)
    .then((info) => {
      if (fs.existsSync(info.path)) {
        res.setHeader('Content-Disposition', 'attachment; filename=' + info.file)
        res.sendFile(info.path, (err) => {
          if (err)
            console.error('Error sending file', err)
          fs.unlinkSync(info.path)
        })
      } else {
        console.error('Missing file', info.path)
        res.setHeader('Content-Type', 'text/plain')
        res.send('Missing output file.')
      }
    })
    .catch((e) => {
      res.setHeader('Content-Type', 'text/plain')
      res.send(e.toString())
      console.error(e)
    })
}

function main() {
  if (process.version < '8.5') {
    console.error('Requires node.js 8.5 or above, not', process.version)
    process.exit(1)
  }

  const args = minimist(process.argv.slice(2))

  // Render the server if a port is specified
  // If no arguments are specified, start the server on a default port
  // Otherwise, treat it as a command line execution
  if (args.port || Object.keys(args).length <= 1) {
    const tmpdir = tmp.dirSync({unsafeCleanup: true})
    render_dir = tmpdir.name
    app = express()
      .use(bodyParser.urlencoded({extended: false}))
      .use((req, res, next) => {
        res.setHeader('Server', server_version)
        next()
      })
      .get('/', webapp)
      .post('/', webapp)
    const port = args.port || default_port
    server = app.listen(port)
      .on('error', (e) => {
        console.error('Could not bind to port', port, e)
        process.exit()
      })
      .on('listening', () => {
        let proc = ('node.js: ' + process.version + ' chromecapture.js: ' + version +
                    ' port: ' + port + ' pid: ' + process.pid)
        console.log(proc)
        function exit(how) {
          console.log('Ending', proc, 'by', how)
          tmpdir.removeCallback()
          server.close()
        }
        process.on('SIGINT', exit.bind(null, 'SIGINT'))
        process.on('exit', exit.bind(null, 'exit'))
        process.on('SIGUSR1', exit.bind(null, 'SIGUSR1'))
        process.on('SIGUSR2', exit.bind(null, 'SIGUSR2'))
      })
  } else {
    render(args).then((info) => {
      console.log('Saving', args.url, 'to', info.file)
      process.exit()
    }).catch((err) => {
      console.error(err)
      process.exit()
    })
  }
}

main()
