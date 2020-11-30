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

$('body').on('click', 'button#toggle-source', function() {
  if($('.btn.viewsource').hasClass('d-none')) {
    $('.btn.viewsource').removeClass('d-none')
    $('.sourcecode-container').removeClass('d-none')
  } else {
    $('.btn.viewsource').addClass('d-none')
    $('.sourcecode-container').addClass('d-none')
  }
})
