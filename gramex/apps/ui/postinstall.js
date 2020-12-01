/* eslint-env node */

const fs = require('fs')
const os = require('os')
const path = require('path')
const child_process = require('child_process')

// Create themes
// --------------------------------------------------------------------
const theme_dir = mkdir(__dirname, 'theme')

// https://bootswatch.com/
// For each bootswatch/dist/<theme>/ directory, add a theme/bootswatch/<theme>.scss that imports
// variables.scss and bootswatch.scss files, with Bootstrap sandwiched in-between.
const bootswatch_root = path.join(__dirname, 'node_modules', 'bootswatch', 'dist')
fs.readdir(bootswatch_root, function (err, files) {
  const target_dir = mkdir(theme_dir, 'bootswatch')
  files.forEach(function (theme) {
    const target = path.join(target_dir, theme + '.scss')
    fs.writeFileSync(target, `// https://bootswatch.com/${theme}/
@import "node_modules/bootswatch/dist/${theme}/variables";
@import "gramexui";
@import "node_modules/bootswatch/dist/${theme}/bootswatch";
`)
  })
})

// http://bootstrap.themes.guide/
// For each bootstrap-theme/src/<theme>/theme.scss, add a theme/themes-guide/<theme>.scss
// replacing the @import bootstrap with gramexui
const tmp = os.tmpdir()
child_process.execSync('rm -rf bootstrap-themes', { cwd: tmp })
child_process.execSync('git clone https://github.com/ThemesGuide/bootstrap-themes.git', { cwd: tmp })
const bootstrap_theme_src = path.join(tmp, 'bootstrap-themes', 'src')
fs.readdir(bootstrap_theme_src, function (err, files) {
  const target_dir = mkdir(theme_dir, 'themes-guide')
  files.forEach(function (dir) {
    const theme_file = path.join(bootstrap_theme_src, dir, 'theme.scss')
    if (fs.existsSync(theme_file)) {
      fs.writeFileSync(path.join(target_dir, `${dir}.scss`),
        fs.readFileSync(theme_file, 'utf8')
          .replace('@import "bootstrap";', '@import "gramexui";')
          // Themes Guide disables grid classes. But we want to use them, so kill this line
          .replace('$enable-grid-classes:false;\n', ''))
    }
  })
  child_process.execSync('rm -rf bootstrap-themes', { cwd: tmp })
})


// Utility functions
// --------------------------------------------------------------------
function mkdir(...dirs) {
  const dir = path.join(...dirs)
  if (!fs.existsSync(dir))
    fs.mkdirSync(dir)
  return dir
}
