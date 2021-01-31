/* globals form_id, hljs, current_form_id */

$(function() {
  $('.btn.viewsource').addClass('d-none')
  $.ajax(`../embed/${form_id}.html`, {
    success: function(data) {
      $('#view-form form').html(data)
      $('pre code.language-html').html(escapeHtml($('#view-form form').html()))
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

$('body').on('click', 'button[data-form]', function () {
  current_form_id = $(this).data('form')
}).on('click', '.confirm-remove', function() {
  $.ajax('../publish', {
    method: 'DELETE',
    data: {id: current_form_id},
    success: function() {
      $('#removeModal').modal('hide')
      $('.toast-body').html('Removed form. Redirecting to the home page...')
      $('.toast').toast('show')
      setTimeout(function() {
        window.location = "../"
      }, 2000)
    }
  })
})
