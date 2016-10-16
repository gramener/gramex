$('.codehilite').each(function() {
  $(this).prepend('<button class="copy-button">copy</button>')
})

new Clipboard('.copy-button', {
  target: function(trigger) {
    return trigger.nextElementSibling
  }
})

anchors.options.placement = 'left'
anchors.add()
