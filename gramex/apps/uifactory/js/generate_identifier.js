/* exported generate_id, replace_double, split_options */

/**
  * Generate identifier for components.
  * @returns String
*/
function generate_id() {
  return Math.random().toString(36).substring(7)
}

function replace_double(value) {
  return value.replace(/"/g, '&quot;')
}

function split_options(options) {
  return options.match(/"[^"]*"|[^,]+/g)
}
