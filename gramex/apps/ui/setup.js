/* eslint-env node */

const fs = require('fs')
const os = require('os')
const path = require('path')
const { execSync } = require('child_process')

// Create themes
// --------------------------------------------------------------------
const theme_dir = mkdir(__dirname, 'theme')
const themes = ['default', 'bootstrap5']

// https://bootswatch.com/
// For each bootswatch/dist/<theme>/ directory, add a theme/bootswatch/<theme>.scss that imports
// variables.scss and bootswatch.scss files, with Bootstrap sandwiched in-between.
const bootswatch_root = path.join(__dirname, 'node_modules', 'bootswatch', 'dist')
const bootswatch_target = mkdir(theme_dir, 'bootswatch')
fs.readdirSync(bootswatch_root).forEach(function (theme) {
  const target = path.join(bootswatch_target, theme + '.scss')
  fs.writeFileSync(target, `// https://bootswatch.com/${theme}/
@import "node_modules/bootswatch/dist/${theme}/variables";
@import "gramexui";
@import "node_modules/bootswatch/dist/${theme}/bootswatch";
`)
  themes.push(`bootswatch/${theme}`)
})

// http://bootstrap.themes.guide/
// For each bootstrap-theme/src/<theme>/theme.scss, add a theme/themes-guide/<theme>.scss
// replacing the @import bootstrap with gramexui
const tmp = os.tmpdir()
execSync('rm -rf bootstrap-themes', { cwd: tmp })
execSync('git clone https://github.com/ThemesGuide/bootstrap-themes.git', { cwd: tmp })
const themes_guide_root = path.join(tmp, 'bootstrap-themes', 'src')
const themes_guide_target = mkdir(theme_dir, 'themes-guide')

fs.readdirSync(themes_guide_root).forEach(function (dir) {
  const theme_file = path.join(themes_guide_root, dir, 'theme.scss')
  if (fs.existsSync(theme_file)) {
    fs.writeFileSync(path.join(themes_guide_target, `${dir}.scss`),
      fs.readFileSync(theme_file, 'utf8')
        .replace('@import "bootstrap";', '@import "gramexui";')
        // Themes Guide disables grid classes. But we want to use them, so kill this line
        .replace('$enable-grid-classes:false;\n', ''))
    themes.push(`themes-guide/${dir}`)
  }
})
execSync('rm -rf bootstrap-themes', { cwd: tmp })

// Save list of themes
fs.writeFileSync('theme/themes.json', JSON.stringify({ 'themes': themes }))


// Utility functions
// --------------------------------------------------------------------
function mkdir(...dirs) {
  const dir = path.join(...dirs)
  if (!fs.existsSync(dir))
    fs.mkdirSync(dir)
  return dir
}
