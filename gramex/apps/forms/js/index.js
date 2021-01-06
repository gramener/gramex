var forms, current_form_id, form_action, form_name

$(function() {
  render_forms()
})

function render_forms() {
  fetch('publish')
    .then(response => response.json())
    .then(function(data) {
      forms = data
      $('.forms').template({forms: data})
    })
}

/**
 * Render toast after form removal or renaming
 * @param {String} msg
 * @param {String} el
 */
function post_action(msg, el) {
  $(el).modal('hide')
  $('.toast-body').html(msg)
  $('.toast').toast('show')
  setTimeout(function() {
    render_forms()
  }, 2000)
}

$('body').search()
$('body').urlfilter()
$(window).on('#?field', function(e, field) {
  $('.card').addClass('d-none')
  $("a:contains(" + field + ")").closest('.card').removeClass('d-none')
}).urlchange()

$('body').on('click', 'button[data-form]', function () {
  current_form_id = $(this).data('form')
  form_action = $(this).data('formaction')
  form_name = $(this).data('formname')
  $('#new-name').val(form_name)
}).on('click', '.confirm-remove', function() {
  $.ajax('publish', {
    method: 'DELETE',
    data: {id: current_form_id},
    success: function() {
      post_action('Removed form. Refreshing the list.', '#removeModal')
    }
  })
}).on('click', '.confirm-rename', function() {
  // need to know the form's metadata before we can edit its name. so fetch it first then update the name.
  fetch(`publish?id=${current_form_id}`)
  .then(response => response.json())
  .then(function(response) {
    let _metadata = JSON.parse(response[0].metadata)
    _metadata.name = $('#new-name').val() || form_name
    $.ajax('publish', {
      method: 'PUT',
      data: {metadata: JSON.stringify(_metadata), id: current_form_id},
      success: function() {
        post_action('Updated name. Refreshing the list.', '#renameModal')
      }
    })
  })
})
