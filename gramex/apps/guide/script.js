// Add a copy button to each .codehilite
$('.codehilite')
  .css('position', 'relative')
  .attr('title', 'Copy code')
  .each(function() {
    $(this).prepend('<button class="copy-button copy-button btn btn-xs btn-dark text-uppercase pos-tr mt-2 mr-n2"><i class="fas fa-copy"></i></button>')
  })
new Clipboard('.copy-button', {
  target: function(trigger) {
    return trigger.nextElementSibling
  }
})

// If an example has render:html or render:js, render code from the next PRE tag
var nodeIterator = document.createNodeIterator(
  document.body,
  NodeFilter.SHOW_COMMENT,
  { acceptNode: function () { return NodeFilter.FILTER_ACCEPT } }
)
while (nodeIterator.nextNode()) {
  var commentNode = nodeIterator.referenceNode
  var match = commentNode.textContent.match(/render:(html|js)/i)
  if (!match)
    continue
  var $code = $(commentNode).next('.codehilite')
  var lang = match[1].toLowerCase()
  if (lang == 'html')
    $('<div class="mx-n3 px-3 mt-n3 mb-3 py-3 bg-light border">' + $code.text() + '</div>').insertAfter($code)
  else if (lang == 'js')
    $('<script>' + $code.text() + '</script>').insertAfter($code)
}

// Show or hide menu based on window size
function toggle_menu(e) {
  $('.menu')[e.matches ? 'addClass' : 'removeClass']('show')
}
var mq = window.matchMedia('(min-width:1024px)')
toggle_menu(mq)
mq.addListener(toggle_menu)

// Add anchors
anchors.options.placement = 'left'
anchors.add()
