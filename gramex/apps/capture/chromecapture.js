/* eslint-env es6, node */
/* eslint-disable no-console */

const puppeteer = require('puppeteer')
const image_size = require('fast-image-size')
const bodyParser = require('body-parser')
const minimist = require('minimist')
const express = require('express')
const cookie = require('cookie')
const path = require('path')
const url = require('url')
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

function delay(ms) {
  return new Promise(res => setTimeout(res, ms))
}


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
  let target = path.join(render_dir, file)
  if (fs.exists(target))
    fs.unlinkSync(target)

  if (typeof browser == 'undefined')
    browser = await puppeteer.launch({args: ['--no-sandbox', '--disable-setuid-sandbox']})
  if (typeof page == 'undefined')
    page = await browser.newPage()
  // Clear past cookies
  let cookies = await page.cookies(q.url)
  await page.deleteCookie(...cookies)
  // Parse cookies and set them on the page, so that they'll be sent on any
  // requests to this URL
  if (q.cookie) {
    let cookieList = []
    let cookieObj = cookie.parse(q.cookie)
    for (let key in cookieObj)
      cookieList.push({name: key, value: cookieObj[key], url: q.url})
    await page.setCookie(...cookieList)
  }
  await page.goto(q.url)
  await delay(q.delay || 0)
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
      // Convert to arrays
      for (let key of ['selector', 'title', 'x', 'y'])
        if (!Array.isArray(q[key]))
          q[key] = [q[key]]
      const image_files = []
      for (const [index, [selector, title, x, y]] of _.zip(q.selector, q.title, q.x, q.y).entries()) {
        options.path = target.replace(/\.pptx$/, '.' + index + '.png')
        image_files.push(options.path)
        await screenshot(page, options, selector)
        const fmt = pptx_size[q.layout in pptx_size ? q.layout : '4x3']
        pptx.setSlideSize(fmt[0] * 72, fmt[1] * 72)
        const slide = pptx.makeNewSlide()
        const dpi = +(q.dpi || 96)
        const size = image_size(options.path)
        slide.addImage(options.path, {
          x: typeof x == 'undefined' ? 'c' : x / dpi * 72,
          y: typeof y == 'undefined' ? 'c' : y / dpi * 72,
          cx: size.width / dpi * 72,
          cy: size.height / dpi * 72
        })
        if (typeof title != 'undefined')
          slide.addText(title, 0, 0, '100%', 36)
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
