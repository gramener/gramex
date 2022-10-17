/* globals module */

module.exports = {
  plugins: [
    "template", // Handle Tornado templates and JS in HTML files
  ],
  env: {
    es6: true, // Allow ES6 in JavaScript
    browser: true, // Include browser globals
    jquery: true, // Include jQuery and $
  },
  globals: {
    _: true, // underscore.js
    d3: true, // d3.js
    vg: true, // vega.js
    L: true, // leaflet.js
    ga: true, // Google analytics
    G: true, // G.min.js
    topojson: true, // topojson.js
    moment: true, // moment.js
    numeral: true, // numeral.js
    assert: true, // chai.js
  },
  extends: "eslint:recommended",
  rules: {
    /* Override default rules */
    "no-global-assign": ["off"], // TODO: avoid current_form_id as a global
  },
};
