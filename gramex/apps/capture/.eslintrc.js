module.exports = {
  "parserOptions": {
    "ecmaVersion": 2017,
    "sourceType": "module"
  },
  "env": {
    "browser": true,    // We have a browser environment in Chrome & PhantomJS
    "amd": true         // use es6 linting
  },
  "globals": {
    "_": true,          // underscore.js
    "Clipboard": true,  // clipboard.js
    "anchors": true     // anchor.js
  }
};
