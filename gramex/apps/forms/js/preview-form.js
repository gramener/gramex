/* globals form_id */

$(function() {
  $('.btn.viewsource').addClass('d-none')
  $.ajax(`../embed/${form_id}.html`, {
    success: function(data) {
      $('#view-form form').html(data + '<button class="btn btn-primary" type="submit">Submit</button>')
      $('pre code.language-html').html(
        escapeHtml($('#view-form form').html())
      )
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

$('body').on('submit', 'form.analytics', function (e) {
  e.preventDefault()
  let $icon = $('<i class="fa fa-spinner fa-2x fa-fw align-middle"></i>').appendTo(this)
  current_form_id = $(this).data('form')
  let _vals = {}
  $.each($('form').serializeArray(), function() { _vals[this.name] = this.value })
  $.ajax(`../analytics/?db=${form_id}&form_id=${form_id}&response=${JSON.stringify(_vals)}`, {
    method: 'POST',
    success: function() {
      $('.toast-body').html('Your response has been recorded.')
      $('.toast').toast('show')
    },
    complete: function() { $icon.fadeOut() }
  })
})
