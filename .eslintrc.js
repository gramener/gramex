/* eslint-env node */

// This file has common options for all Gramex apps
// See https://eslint.org/docs/user-guide/configuring
// To override for specific apps, add it in package.json > eslintConfig
// ... or add a .eslintrc.js
module.exports = {
  parserOptions: {
    ecmaVersion: "latest",
  },
  env: {
    browser: true,
    es6: true
  },
  // These default plugins are installed in the root gramex director via package.json
  plugins: ["html", "template"],
  // Styles are based on recommended eslint fields, but with specific overrides
  extends: "eslint:recommended",
};
