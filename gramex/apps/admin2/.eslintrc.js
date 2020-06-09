/* eslint-env node */
module.exports = {
  'overrides': [{
    'files': [
      'rollup.config.js',
      'schedule.src.js'
    ],
    'parserOptions': {
      'sourceType': 'module',
    }
  }],
  'ignorePatterns': [
    'schedule.js'         // generated by schedule.src.js
  ]
}
