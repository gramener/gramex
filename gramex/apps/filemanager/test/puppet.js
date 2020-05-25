/* eslint-env browser, node */
const glob = require('glob')

async function run_puppeteer() {
  const puppeteer = require('puppeteer')
  const browser = await puppeteer.launch({
    // On Gitlab CI, running as root without --no-sandbox is not supported
    args: ['--no-sandbox']
  })
  const page = await browser.newPage()
  // Note: if there's a console error, msg.type == 'error'. msg.args has error arguments.
  page.on('console', msg => console.log(msg.text()))    // eslint-disable-line no-console
  const paths = glob.sync('test-*.html')
  for (let i = 0; i < paths.length; i++) {
    let url = 'http://localhost:9999/' + paths[i]
    await page.goto(url)
    try {
      await page.waitForFunction('window.renderComplete')
    } catch (e) {
      console.log('not ok ' + paths[i])
    }
  }
  await browser.close()
}
run_puppeteer()
