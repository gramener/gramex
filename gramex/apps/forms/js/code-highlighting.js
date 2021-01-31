/* globals ClipboardJS */

/* Prism copy to clipboard for all pre with viewsource class */
// ref: https://stackoverflow.com/a/34198183
$('pre.viewsource').each(function () {
  var $this = $(this)
  var $button = $('<button class="btn-sm" type="button">Copy</button>')
  $this.wrap('<div/>').removeClass('viewsource')
  var $wrapper = $this.parent()
  $wrapper.addClass('viewsource-wrapper').css({position: 'relative'})
  $button.css({position: 'absolute', top: 10, right: 10}).appendTo($wrapper).addClass('viewsource btn btn-light')
  var copyCode = new ClipboardJS('button.viewsource', {
    target: function (trigger) {
      return trigger.previousElementSibling
    }
  })
  copyCode.on('success', function (event) {
    event.clearSelection()
    event.trigger.textContent = 'Copied'
    window.setTimeout(function () {
      event.trigger.textContent = 'Copy'
    }, 2000)
  })
  copyCode.on('error', function (event) {
    event.trigger.textContent = 'Press "Ctrl + C" to copy'
    window.setTimeout(function () {
      event.trigger.textContent = 'Copy'
    }, 2000)
  })
})
