/* globals form_id */

$(function() {
  $('.btn.viewsource').addClass('d-none')
  $.ajax(`../embed/${form_id}.html`, {
    success: function(data) {
      $('#view-form').html(data)
      $('pre code.language-html').html(escapeHtml($('#view-form').html()))
      document.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightBlock(block)
      })
    }
  })

  $('svg').urlfilter()
})

// escape html tags to show source code
function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
