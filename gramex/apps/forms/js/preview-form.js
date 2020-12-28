/* globals form_id */

$(function() {
  console.log("here")
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

// $(function() {
  console.log("where?")
  // setTimeout(function () {
    $('body').on('submit', 'form.analytics', function (e) {
      e.preventDefault()
      console.log("e", e)
      current_form_id = $(this).data('form')
    // }).on('click', 'button[type="submit"]', function(e) {
      console.log("...", form_id, `../analytics/?db=${form_id}`)
      $.ajax(`../analytics/?db=${form_id}&form_id=${form_id}&response=${$('form').serialize()}`, {
        method: 'POST',
        data: $('form').serialize(),
        success: function() {
          $('#removeModal').modal('hide')
          $('.toast-body').html('Removed form. Redirecting to the home page...')
          $('.toast').toast('show')
        }
      })
    })
  // }, 3000)
// })
