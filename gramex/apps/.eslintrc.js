module.exports = {
  "parserOptions": {
    "ecmaVersion": 6    // Use ES6 parser. Browsers other than IE support it
  },
  "plugins": [
    "template"          // Handle Tornado templates and JS in HTML files
  ],
  "env": {
    "es6": true,        // Allow ES6 in JavaScript
    "browser": true,    // Include browser globals
    "jquery": true,     // Include jQuery and $
    "mocha": true       // Include it(), assert(), etc
  },
  "globals": {
    "_": true,          // underscore.js
    "d3": true,         // d3.js
    "vg": true,         // vega.js
    "L": true,          // leaflet.js
    "ga": true,         // Google analytics
    "g1": true,         // g1.min.js
    "topojson": true,   // topojson.js
    "moment": true,     // moment.js
    "numeral": true,    // numeral.js
    "assert": true      // chai.js
  },
  "extends": "eslint:recommended",
  "rules": {
    /* Override default rules */
    "indent": [2, 2, { "VariableDeclarator": 2 }],  // Force 2 space indentation
    "linebreak-style": 2,           // Force UNIX style line
    "quotes": [1, "single"],        // Prefer double-quotes style
    "semi": [1, "never"]            // Prefer no-semicolon style
  }
};
