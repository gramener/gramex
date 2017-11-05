/* globals cookie */
/* exported xsrf, pre */

var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
var pre = [].slice.call(document.querySelectorAll('pre'))

function next() {
  var element = pre.shift()
  var text = element.textContent
  if (text.match(/\$.(ajax|get|post)/)) {
    eval(text)
      .always(function(result) {
        element.innerHTML = element.innerHTML.replace(/OUTPUT/, 'OUTPUT<br>' + JSON.stringify(result, null, 2))
        if (pre.length > 0) next()
      })
  }
  else if (pre.length > 0) next()
}
next()
