/* eslint no-console: 0 */

const path = require('path')
const express = require('express')
const glob = require('glob')

var g1 = require('./../node_modules/g1/dist/g1.js')
var fs = require('fs')
const port = process.argv.length <= 2 ? 1112 : 1113
var data = JSON.parse(fs.readFileSync('./test/default-drive.json', { encoding: "utf8" }))

const app = express()
  .use(express.static(path.resolve(__dirname, '..')))

app.route('/default').get(function(req, res) {
  res.send(data)
})

app.route('/default').post(function(req, res) {
  console.log(req.body)
})

app.route('/default').put(function(req, res) {
  console.log(req.body)
  res.send([])
})

async function run_puppeteer() {
  const puppeteer = require('puppeteer')
  const browser = await puppeteer.launch({
    // On Gitlab CI, running as root without --no-sandbox is not supported
    args: ['--no-sandbox']
  })
  const page = await browser.newPage()
  // Note: if there's a console error, msg.type == 'error'
  // msg.args has the error arguments.
  page.on('console', msg => console.log(msg.text))    // eslint-disable-line no-console
  const paths = glob.sync('test/test-*.html')
  for (let i = 0; i < paths.length; i++) {
    let url = 'http://localhost:' + port + '/' + paths[i]
    await page.goto(url)
    console.log(url)
    try {
      await page.waitForFunction('window.renderComplete')
    } catch (e) {
      console.log('not ok ' + paths[i])
    }
  }
  await browser.close()
  server.close()
}

async function run_selenium(browser) {
  const { Builder } = require('selenium-webdriver')
  const driver = await new Builder().forBrowser(browser).build()
  const paths = glob.sync('test/test-*.html')
  for (let i = 0; i < paths.length; i++) {
    let url = 'http://localhost:' + port + '/' + paths[i]
    try {
      await driver.get(url)
      let logs = await driver.wait((driver) => driver.executeScript('return window.renderComplete'), 30000)
      console.log(logs.join(''))
    } catch (e) {
      console.log('not ok ' + paths[i])
    }
  }
  await driver.quit()
  server.close()
}

const server = app.listen(port, function () {
  // If run as "node server.js", start the HTTP server for manual testing
  if (process.argv.length <= 2)
    console.log('Server running on port ' + port)   // eslint-disable-line no-console
  // If run as "node server.js <browser>", run browser on each and show console log
  else {
    let browser = process.argv[2].toLowerCase()
    if (browser == 'puppeteer')
      run_puppeteer()
    else
      run_selenium(browser)
  }
})
