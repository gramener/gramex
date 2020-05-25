/* eslint-env node */

// This file has common options for all Gramex apps
// See https://eslint.org/docs/user-guide/configuring
// To override for specific apps, add it in package.json > eslintConfig
// ... or add a .eslintrc.js
module.exports = {
  'parserOptions': {
    'ecmaVersion': 6    // Use ES6 parser. Browsers other than IE support it
  },
  // These default plugins are installed in the root gramex director via package.json
  'plugins': [
    'html',
    'template'
  ],
  // Styles are based on recommended eslint fields, but with specific overrides
  'extends': 'eslint:recommended',
  'rules': {
    'indent': [2, 2, { 'VariableDeclarator': 2 }],  // Force 2 space indentation
    'linebreak-style': 2,           // Force UNIX style line
    'quotes': [1, 'single'],        // Prefer double-quotes style
    'semi': [1, 'never']            // Prefer no-semicolon style
  }
}
