/* globals initiate_copy */

var current_form_id, form_name

$(function() {
  render_forms()
})

/**
  * Render forms on page load or on a form rename or on making a form a template
*/
function render_forms() {
  fetch('publish')
    .then(response => response.json())
    .then(function(data) {
      // parse metadata as JSON
      // filter forms by template type and non template type
      let _data = _.each(data, function(item) { item.metadata = JSON.parse(item.metadata); })
      let _forms = _.filter(_data, function(item) { return Object.keys(item.metadata).indexOf('template') > -1 ? '' : item })
      let templates = _.filter(_data, function(item) { return Object.keys(item.metadata).indexOf('template') > -1 ? item : '' })
      $('.forms').template({forms: _forms})
      $('.form-templates').template({templates: templates})
      _forms.length = 0
      if(_forms.length > 0) {
        $('.recent-forms-header').removeClass('d-none')
        $('.form-card').removeClass('d-none')
      }
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
}).on('click', '[data-formaction]', function() {
  if($(this).data('formaction') === 'copy')
    initiate_copy('.', $(this).data('form'))
  else if($(this).data('formaction') === 'template')
    // update form.metadata.template = 1
    // make_form_template('.', $(this).data('form'))
    initiate_copy('.', $(this).data('form'), true);
})
