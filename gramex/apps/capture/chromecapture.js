/* eslint-env browser, es6, node */
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

let browser, app, server
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
        if (!rect || !rect.width || !rect.height) return
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


function templatize(input) {
  // Convert input into header / footer template.
  return input
    .replace(/\$\w+/g, (match) => `<span class="${match.slice(1)}"></span>`)
    .split('|')
    .map(v => `<span>${v}</span>`)
    .join('')
}

const browser_setup = async (args) => {
  browser = await puppeteer.launch({args: args})
  browser.on('disconnected', () => {
    console.log('Reconnecting browser')
    browser.close()
    browser_setup(args)
  })
  return browser
}

async function render(q) {
  console.log('Opening', q.url)

  let ext = q.ext || 'pdf'
  let media = q.media || 'screen'
  let file = (q.file || 'screenshot') + '.' + ext
  let headers = q.headers || {}
  let target = tmp.tmpNameSync({ dir: render_dir, postfix: file })
  let pdf_options = {
    path: target,
    format: q.format || 'A4',
    landscape: q.orientation == 'landscape',
    scale: parseFloat(q.scale || 1),  // scale must be a double, not int
    margin: {},
    printBackground: true,
  }
  // If margins are specified, use them
  let margin_keys = ['top', 'right', 'bottom', 'left']
  if (q.margins)
    pdf_options['margin'] = _.zipObject(margin_keys, q.margins.split(','))
  function template_wrap(s) {
    return `<div style="
      margin-left:${pdf_options.margin.left || '1cm'};
      margin-right:${pdf_options.margin.right || '1cm'};
      zoom:0.75;
      font-size:10px;
      display:flex;
      justify-content:space-between;
      width:100%">${s}</div>`
  }
  if (q.header || q.headerTemplate || q.footer || q.footerTemplate) {
    // For zoom: TODO: https://stackoverflow.com/a/51461829/100904
    // If displayHeaderFooter, headerTemplate and footerTemplate MUST BOTH be present
    pdf_options.displayHeaderFooter = true
    pdf_options.headerTemplate = template_wrap(q.headerTemplate || templatize(q.header || ''))
    pdf_options.footerTemplate = template_wrap(q.footerTemplate || templatize(q.footer || ''))
    // Increase default margin if header / footer is present
    if (q.header || q.headerTemplate)
      pdf_options.margin.top = pdf_options.margin.top || '2cm'
    if (q.footer || q.footerTemplate)
      pdf_options.margin.bottom = pdf_options.margin.bottom || '2cm'
  }
  // Default to 1cm margin if none was specified
  _.each(margin_keys, key => pdf_options.margin[key] = pdf_options.margin[key] || '1cm')
  let args = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--ignore-certificate-errors'
  ]
  // If a proxy environment variable is defined, use it
  let proxy = process.env.HTTPS_PROXY || process.env.HTTP_PROXY || process.env.ALL_PROXY
  if (proxy)
    args.push('--proxy-server=' + proxy)

  if (typeof browser == 'undefined')
    browser = await browser_setup(args)

  let page = await browser.newPage()

  page
    .on('console', message => console.log(`${message.type().toUpperCase()} ${message.text()}`))
    .on('pageerror', error => console.log(`ERROR: ${error.message}`))
    .on('response', response => {
      if (response.status() >= 400)
        console.log(`HTTP ${response.status()}: ${response.url()}`)
    })
    .on('requestfailed', request => console.log(`${request.failure().errorText}: ${request.url()}`))

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

  if (q.emulate) {
    let device = Object.assign({}, puppeteer.devices[q.emulate])
    device.viewport.deviceScaleFactor = +q.scale || device.viewport.deviceScaleFactor
    await page.emulate(device)
  } else {
    await page.setViewport({
      width: +q.width || 1200,
      height: +q.height || 768,
      deviceScaleFactor: +q.scale || 1    // Apply for PDF?
    })
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
    await page.pdf(pdf_options)
  } else {
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
  await page.close()
  if (q._test_disconnect){
    console.log('Disconnecting browser')
    browser.disconnect()
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
        res.status(500).send('Missing output file.')
      }
    })
    .catch((e) => {
      console.error(e)
      res.setHeader('Content-Type', 'text/plain')
      res.status(500).send(e.toString())
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
