/* globals user, active_form_id, _user_form_config, fields, generate_id, kebabize */
/* exported editor */

let editor
$('.field-actions').template({base: '.'})

$(window).on('click', function(e) {
  if(!$(e.target).closest('.edit-properties').length && !$(e.target).closest('.user-form').length) {
    $('.edit-properties').empty()
    $('.user-form > *').removeClass('highlight')
    $('.actions').addClass('d-none')
  }
})

function render_form_from_json(_json) {
  _.each(_json, function(opts) {
    let dir = opts.component
    // _user_form_config only retains attributes from fields.js, `id` isn't captured
    $(`<${dir} id="${generate_id()}"></${dir}>`)
      .appendTo('.user-form')
      .attr(opts)
  })
}

$(function() {
  // add fields to the modal which can be viewed on + click in user form on the left
  for(let field in fields) {
    $(`<${field}></${field}>`).appendTo('.form-fields')
    $('<div class="divider"></div>').appendTo('.form-fields')
  }

  // render existing form using JSON
  if(active_form_id) {
    $('.edit-properties-title').removeClass('d-none')
    render_form_from_json(_user_form_config)
  }
  $('body').search()
})

/**
  * updates configuration for an existing form
  * @param {Object} form_details
*/
function update_existing_form(form_details, $icon) {
  $.ajax('publish', {
    method: form_details.method,
    data: form_details.data,
    success: function () {
      $('.post-publish').removeClass('d-none')
    },
    error: function () {
      $('.toast-body').html('Unable to update the form. Please try again later.')
      $('.toast').toast('show')
    },
    complete: function() { $icon.fadeOut() }
  })
}

/**
  * creates configuration for a new form
  * @param {Object} form_details
*/
function create_new_form(form_details, $icon) {
  $.ajax('publish', {
    method: form_details.method,
    data: form_details.data,
    success: function (response) {
      form_details.id = response.data.inserted[0].id
      $('.post-publish').removeClass('d-none')
      $('.form-preview-link').html(`<a class="btn btn-info" href="form/${form_details.id}" target="_blank">Preview</a>`)
      $('.form-view-link').html(`<a class="btn btn-success" href="view/${form_details.id}" target="_blank">View</a>`)
      window.location.href = `create?id=${form_details.id}`
    },
    error: function () {
      $('.toast-body').html('Unable to publish the form. Please try again later.')
      $('.toast').toast('show')
    },
    complete: function() { $icon.fadeOut() }
  })
}

function prepare_form_values(_values) {
  let form_values = []
  let _html = ''
  $('.user-form > :not(.actions)').each(function(ind, item) {
    _html += item.outerHTML
    _values = item.__model
    _values['component'] = item.tagName.toLowerCase()
    if(_values.component === 'bs4-html')
    _values.value = _values.value.replace(/\n/g, "\\n")
    if(typeof item !== undefined) {
      delete _values.$target
      form_values.push(_values)
    }
  })
  return {_form: form_values, _html: _html}
}

$('body').on('click', '#publish-form', function() {
  let _values = {}
  let $icon = $('<i class="fa fa-spinner fa-2x fa-fw align-middle"></i>').appendTo(this)
  let _md = {
    name: $('#form-name').val() || 'Untitled',
    categories: [],
    description: $('#form-description').val().trim() || 'Form description'
  }

  $('.edit-properties > input, .edit-properties > input').each(function(ind, item) { _values[item.id] = item.value })
  $('.user-form > *').removeClass('highlight')
  $('.edit-properties').empty()

  let { _form, _html } = prepare_form_values(_values)
  let form_details = {
    data: {
      config: JSON.stringify(_form),
      html: _html,
      metadata: JSON.stringify(_md),
      user: user
    }
  }

  if(active_form_id.length > 0) {
    form_details.data.id = active_form_id
    form_details.method = 'PUT'
    update_existing_form(form_details, $icon)
  } else {
    // POST creates a new identifier
    delete form_details.data.id
    form_details.method = 'POST'
    create_new_form(form_details, $icon)
  }
}).on('click', '.form-fields > *:not(.divider)', function() {
  // every field added to .user-form will have a new identifier
  this.id = generate_id()
  var _type = this.tagName.toLowerCase()
  let _local_values = JSON.parse(JSON.stringify(fields[_type]))
  let vals = _.mapValues(_.keyBy(_local_values, 'name'), 'value')
  $(`.form-fields > ${_type}`)
    .data('type', _type)
    .data('vals', vals)
    .clone()
    .appendTo('.user-form')
  $('#publish-form').removeClass('d-none')
  $('.btn-link').removeClass('d-none')
  $('#addFieldModal').modal('hide')
}).on('click', '[data-action]', function() {
  const form_el = $(this).parent().parent().next()
  if($(this).data('action') === 'duplicate') {
    form_el.removeClass('highlight')
    form_el.clone().attr('id', generate_id()).insertAfter(form_el)
  } else if($(this).data('action') === 'delete') {
    form_el.remove()
  }
  $('.edit-properties').empty()
  $('.user-form > *').removeClass('highlight')
  $('.actions').addClass('d-none')
})

$('body').on('click', '.user-form > :not(.actions)', function () {
  let this_el = $(this)
  let this_field = $(this).get(0).tagName.toLowerCase()
  $('.edit-properties').empty()
    .data('editing-element', $(this))
  $('.user-form > *').removeClass('highlight')
  $('.edit-properties-title').removeClass('d-none')
  $(this).addClass('highlight')
  $('.actions').insertBefore(this)
  $('.actions').removeClass('d-none')

  // Need access to field's (ex: bs4-button) JSON config to render the attributes on the right side.
  let values = JSON.parse(JSON.stringify(fields[this_field]))
  let names = _.map(values, function(item) { return item.name })
  // __model will have attributes in camelCase (ex: actionsBox for `.selectpicker`)
  let field_properties = this_el.get(0).__model
  for(let key in field_properties) {
    if(names.indexOf(kebabize(key)) !== -1) {
      _.each(values, function(item) {
        if(item.name === kebabize(key)) {
          item.value = encodeURI(field_properties[key])
        }
      })
    }
  }
  _.each(values, function(item) {
    let _el = document.createElement(item.field)
    item.id = generate_id()
    item.origin = this_el.get(0).id
    document.querySelector('.edit-properties').appendChild(_el)
    $(_el).attr(item)
  })
  // retain values on accidental page refresh
  /*eslint-disable no-unused-vars*/
  let { _form, _html } = prepare_form_values({})
  /*eslint-enable no-unused-vars*/
  localStorage.setItem('form', JSON.stringify(_form))
})

// use element.matches instead of tagName.toLowerCase()
// each bs4-* element on the attributes form on the right side will have an origin attribute
// its value is the id of the element that's currently edited
$(document).on('change', '.edit-properties > [origin]', function () {
  let vals = {}
  var $el = $(this).closest('[origin]').get(0)
  var $current_attr = $(this)
  var edited_field = $(`#${$el.getAttribute('origin')}`)

  if($current_attr.find('select').length > 0) {
    // we have found a select element
    vals[$($el).attr('name')] = $current_attr.find('select').val()
  } else if($current_attr.find('.selectpicker').length > 0) {
    // we have found a select element
    vals[$($el).attr('name')] = $current_attr.find('.selectpicker').val()
  } else if(
      $current_attr.attr('field') == 'bs4-text' ||
      $current_attr.attr('field') == 'bs4-email' ||
      $current_attr.attr('field') == 'bs4-number' ||
      $current_attr.attr('field') == 'bs4-range' ||
      $current_attr.attr('field') == 'bs4-textarea' ||
      $current_attr.attr('field') == 'bs4-select') {
      if($current_attr.attr('field') == 'bs4-textarea') {
        // textarea
        vals[$($el).attr('name')] = $current_attr.find('textarea').val()
      } else if ($current_attr.attr('field') == 'bs4-text') {
        vals[$($el).attr('name')] = $current_attr.find('input').val()
      } else {
        // email, number, range, text
        vals[$($el).attr('name')] = $current_attr.find('input').val()
      }
  }
  else if(
      $current_attr.attr('field') === 'bs4-radio' ||
      $current_attr.attr('field') === 'bs4-checkbox') {
    // TODO - not implemented yet
    // since radio and checkbox fields each support multiple options
  } else if($current_attr.attr('field') === 'bs4-html') {
    vals[$el.name] = $current_attr.find('textarea').val()
  } else {
    // handle other attributes
  }
  delete vals[""]
  let _local_el = document.getElementById($el.getAttribute('origin'))
  for(let key in vals) {
    _local_el.setAttribute(key, vals[key])
  }
  // $($(edited_field).get(0)).attr(vals)
  $('.field-actions').template({base: '.'})
  $('.actions').removeClass('d-none')
  $('.actions').insertBefore(edited_field)
})

$('.user-form').on('submit', function(e) {
  e.preventDefault()
})
