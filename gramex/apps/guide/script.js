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
