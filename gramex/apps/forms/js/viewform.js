/* globals form_id, hljs, current_form_id, this_view */

// escape html tags to show source code
function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

$(function() {
  $('.btn.viewsource').addClass('d-none')
  $.ajax(`../embed/${form_id}.html`, {
    success: function(data) {
      $('#view-form form').html(
        this_view === 'form' ? data : data + '<button class="btn btn-primary" type="submit">Submit</button>'
        )
        $('pre code.language-html').html(escapeHtml($('#view-form form').html()))
        document.querySelectorAll('pre code').forEach((block) => {
          hljs.highlightBlock(block)
        })
      }
  })
  $('svg').urlfilter({target: '#'})
})

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
}).on('submit', 'form.analytics', function (e) {
  e.preventDefault()
  let $icon = $('<i class="fa fa-spinner fa-2x fa-fw align-middle"></i>').appendTo(this)
  let field_vals = {}
  // $.each($('form').serializeArray(), function() { _vals[this.name] = this.value })
  // above line fails for checkboxes with multiple values, hence the following approach
  let groups = _.groupBy($('form').serializeArray(), 'name')
  field_vals = _(groups)
    .map((values, _input) => {
      const v = values.map(v => v.value)
      return {_input, v}
    }).value()
  // convert {name: 'checkbox-input', value: ['yes']} to {'checkbox-input': ['yes']}
  field_vals = _.map(field_vals, v => {
    return { [v._input]: v.v }
  })

  $.ajax(`../analytics/?db=${form_id}&form_id=${form_id}&response=${JSON.stringify(field_vals)}`, {
    method: 'POST',
    success: function() {
      $('.toast-body').html('Your response has been recorded.')
      $('.toast').toast('show')
    },
    complete: function() { $icon.fadeOut() }
  })
})
