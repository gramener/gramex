/* globals user, active_form_id, _user_form_config, fields */
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

/**
  * Generate identifier for components.
  * @returns String
*/
function generate_id() {
  return Math.random().toString(36).substring(7)
}

$(function() {
  // add fields to the modal which can be viewed on + click in user form on the left
  for(let field in fields) {
    $(`<${field}></${field}>`).appendTo('.form-fields')
  }

  // render existing form using JSON
  if(active_form_id) {
    _.each(_user_form_config, function(opts) {
      let dir = opts.component
      $(`<${dir}></${dir}>`).attr(opts)
        .appendTo('.user-form')
    })
  }
})

$('body').on('click', '#publish-form', function() {
  let _vals = {}
  $('.edit-properties > input, .edit-properties > input').each(function(ind, item) { _vals[item.id] = item.value })
  $('.user-form > *').removeClass('highlight')
  $('.edit-properties').empty()
  let $icon = $('<i class="fa fa-spinner fa-2x fa-fw align-middle"></i>').appendTo(this)

  let _md = {
    name: $('#form-name').text() || 'Untitled',
    categories: [],
    description: $('#form-description').text().trim()
  }
  let form_vals = []
  $('.user-form > :not(.actions)').each(function(ind, item) {
    _vals = item.__obj
    _vals['component'] = item.tagName.toLowerCase()
    if(_vals.component === 'g-html')
    _vals.value = _vals.value.replace(/\n/g, "\\n")
    if(typeof item !== undefined) {
      delete _vals.$target
      form_vals.push(_vals)
    }
  })
  let form_details = {
    data: {
      config: JSON.stringify(form_vals),
      html: $('#user-form form').html(),
      metadata: JSON.stringify(_md),
      user: user
    }
  }

  if(active_form_id.length > 0) {
    form_details.data.id = active_form_id
    form_details.method = 'PUT'
    // update existing form
    $.ajax('publish', {
      method: 'PUT',
      data: form_details.data,
      success: function () {
        $('.post-publish').removeClass('d-none')
        $('.form-link').html(`<a href="form/${active_form_id}" target="_blank">View</a>`)
      },
      error: function () {
        $('.toast-body').html('Unable to update the form. Please try again later.')
        $('.toast').toast('show')
      },
      complete: function() { $icon.fadeOut() }
    })
  } else {
    // POST creates a new identifier
    delete form_details.data.id
    form_details.method = 'POST'
    $.ajax('publish', {
      method: form_details.method,
      data: form_details.data,
      success: function (response) {
        form_details.id = response.data.inserted[0].id
        $('.post-publish').removeClass('d-none')
        $('.form-link').html(`<a href="form/${form_details.id}" target="_blank">View</a>`)
        window.location.href = `create?id=${form_details.id}`
      },
      error: function () {
        $('.toast-body').html('Unable to publish the form. Please try again later.')
        $('.toast').toast('show')
      },
      complete: function() { $icon.fadeOut() }
    })
  }
}).on('click', '.form-fields > *', function() {
  // every field added to .user-form will have a new identifier
  this.id = generate_id()
  var _type = this.tagName.toLowerCase()
  let vals = _.mapValues(fields[_type], v => v.value)
  vals['view'] = 'updating'
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
    form_el.clone().insertAfter(form_el)
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
  $(this).addClass('highlight')
  $('.actions').insertBefore(this)
  $('.actions').removeClass('d-none')

  // Need access to field's (ex: g-button) JSON config to render the attributes on the right side.
  let vals = fields[this_field]
  let names = _.map(vals, function(item) { return item.name })
  let field_properties = this_el.get(0).__obj
  for(let key in field_properties) {
    if(names.indexOf(key) !== -1) {
      _.each(vals, function(item) {
        if(item.name === key) {
          item.value = field_properties[key]
        }
      })
    }
  }
  _.each(vals, function(item) {
    let _el = document.createElement(item.field)
    item.id = generate_id()
    item.origin = this_el.get(0).id
    $(_el).attr(item)
    document.querySelector('.edit-properties').appendChild(_el)
  })
})

// use element.matches instead of tagName.toLowerCase()
// each g-* element on the attributes form on the right side will have an origin attribute
// its value is the id of the element that's currently edited
$(document).on('change', '.edit-properties > [origin]', function () {
  let vals = {}
  var $el = $(this).closest('[origin]').get(0)
  var $current_attr = $(this)
  var edited_field = $(`#${$el.getAttribute('origin')}`)

  if($(this).find('.selectpicker').length > 0) {
    // we have found a select element
    vals[$($el).attr('name')] = $(this).find('.selectpicker').val()
  } else if(
      $current_attr.attr('field') == 'g-text' ||
      $current_attr.attr('field') == 'g-email' ||
      $current_attr.attr('field') == 'g-number' ||
      $current_attr.attr('field') == 'g-range' ||
      $current_attr.attr('field') == 'g-textarea') {
      if($current_attr.attr('field') == 'g-textarea') {
        // textarea
        vals[$($el).attr('name')] = $current_attr.find('textarea').val()
      } else {
        // email, number, range, text
        vals[$($el).attr('name')] = $current_attr.find('input').val()
      }
  }
  else if(
      $current_attr.attr('field') === 'g-radio' ||
      $current_attr.attr('field') === 'g-checkbox') {
    // TODO - not implemented yet
    // since radio and checkbox fields each support multiple options
  } else if($current_attr.attr('field') === 'g-html') {
    vals[$el.name] = $current_attr.find('textarea').val()
  } else {
    // handle other attributes
  }
  delete vals[""]
  $($(edited_field).get(0)).attr(vals)
  $('.field-actions').template({base: '.'})
  $('.actions').removeClass('d-none')
  // $('.actions').insertBefore($el)
})

$('.user-form').on('submit', function(e) {
  e.preventDefault()
})
