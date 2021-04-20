/* exported generate_id, replace_double, split_options, kebabize */

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

/**
  * Split string
  * example input: 'One, "Two, Three", Four'
  * example output: ["One", "Two, Three", "Four"]
  * @param options
  * @returns Array
*/
function split_options(options) {
  return options.match(/"[^"]*"|[^,]+/g)
}

/**
  * convert attributes (e.g. fontSize) to kebab-case (e.g. font-size)
*/
const kebabize = str => {
  return str.split('').map((letter, idx) => {
    return letter.toUpperCase() === letter
      ? `${idx !== 0 ? '-' : ''}${letter.toLowerCase()}`
      : letter;
  }).join('');
}
