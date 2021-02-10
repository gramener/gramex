/* eslint-env node */
// Create a snippets.json that has the config and template for each snippet.

const fs = require('fs')
const path = require('path')
const config = {}

// Loop through each directory
fs.readdirSync(__dirname, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .forEach(dirent => {
      const dirname = dirent.name
      // If config.json and index.html exist...
      const config_file = path.join(__dirname, dirname, 'config.json')
      const template_file = path.join(__dirname, dirname, 'index.html')
      if (!fs.existsSync(config_file) || !fs.existsSync(template_file))
        return
      // ... read the configuration
      config[dirname] = JSON.parse(fs.readFileSync(config_file))
      config[dirname].template = fs.readFileSync(template_file, { encoding: 'utf8' })
    })

// Write to snippets.json
fs.writeFileSync(path.join(__dirname, 'snippets.json'), JSON.stringify(config))
