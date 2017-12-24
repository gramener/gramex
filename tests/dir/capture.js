// After 500 ms, change color to blue and text to blue block
setTimeout(function() {
  document.querySelector('p').style.color = 'blue'
  document.querySelector('em').innerHTML = 'Blue block'
}, 500)


// After 1000 ms, change color to green and text to green block
// Finally set renderComplete to true
setTimeout(function () {
  document.querySelector('p').style.color = 'green'
  document.querySelector('em').innerHTML = 'Green block'
  window.renderComplete = true
}, 1000)


// Display the cookie value if ?show-cookie is in the URL
if (document.location.search.match(/show-cookie/))
  document.querySelector('.cookie').innerHTML = 'js:cookie=' + document.cookie
