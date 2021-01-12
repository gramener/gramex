/* globals dragula, user, user_name, editor, active_form_id, options */
/* exported editor */

const left = '.drag-fields'
const right = '.user-form'
let editor

$(function () {
  setTimeout(function () {
    dragAndDrop.init()
  }, 300)
}) // anonymous function

var dragAndDrop = {
  limit: 20,
  count: 0,
  init: function () {
    this.dragula();
    this.drake();
  },
  drake: function () {
    this.dragula.on('drop', this.dropped.bind(this));
  },
  dragula: function () {
    this.dragula = dragula([document.querySelector(left), document.querySelector(right)],
    {
      moves: this.canMove.bind(this),
      copy: true,
    });
  },
  canMove: function () {
    return this.count < this.limit;
  },
  dropped: function (el) {
    let _type = $(el).find('label').data('type')
    let vals = _.mapValues(options[_type], v => v.value)
    $(el)
      .data('type', _type)
      .data('vals', vals)

    $('#publish-form').removeClass('d-none')
    $('.btn-link').removeClass('d-none')
  }
};

let dirs = ['button', 'checkbox', 'email', 'number', 'password', 'radio', 'range', 'select', 'text']
const promises = []
const options = {}
const template = {}

dirs.forEach(dir => {
  promises.push(fetch(`snippets/?type=${dir}&file=config&ext=json`)
    .then(response => response.json())
    .then(function(json) { options[dir] = json.options }))
  promises.push(fetch(`snippets/?type=${dir}&file=index&ext=html`)
    .then(response => response.text())
    .then(function(text) { template[dir] = _.template(text) }))
})
Promise.all(promises).then(() => {
  _.each(template, (tmpl, dir) => {
    let vals = _.mapValues(options[dir], v => v.value)
    $(tmpl(vals))
      .data('type', dir)
      .data('vals', vals)
      .appendTo('.drag-fields')
  })
  // TODO: Can we ensure they all have a common parent class? I'll assume it's .form-group
  $('body').on('click', '.user-form .form-group, .user-form .form-check, .user-form button', function () {
    $('.delete-field-trigger').removeClass('d-none')
    $('.edit-properties').empty()
      .data('editing-element', $(this))
    let field_vals = $(this).data('vals')
    _.each(options[$(this).data('type')], function (option, key) {
      let vals = _.mapValues(options[option.field], v => v.value)
      _.extend(vals, option)
      vals.value = field_vals[key]
      $(template[option.field](vals))
        .appendTo('.edit-properties')
        .addClass('form-element')
        .data('key', key)
        .data('field', option.field)
    })
  })
})

$('body').on('click', '#publish-form', function() {
  let $icon = $('<i class="fa fa-spinner fa-2x fa-fw align-middle"></i>').appendTo(this)
  // create a database entry with for_edits
  let _md = {
    name: $('#form-name').val() || 'Untitled',
    categories: [],
    description: $('#form-description').val()
  }
  let form_details = {
    data: {
      config: '',
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
        $('.form-link').html(`<a href="form/${active_form_id}">View form</a>`)
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
        $('.form-link').html(`<a href="form/${form_details.id}">View form</a>`)
      },
      error: function () {
        $('.toast-body').html('Unable to publish the form. Please try again later.')
        $('.toast').toast('show')
      },
      complete: function() { $icon.fadeOut() }
    })
  }
}).on('click', '.edit-html-trigger', function() {
  $('.update-form').removeClass('d-none')
}).on('click', '.update-form', function() {
  let $icon = $('<i class="fa fa-spinner fa-2x fa-fw align-middle"></i>').appendTo(this)
  $('#user-form').html(editor.getValue())
  $icon.fadeOut()
}).on('shown.bs.modal', '#editHTMLModal', function() {
  if(window.monaco !== undefined)
    monaco.editor.getModels().forEach(model => model.dispose())
  require(['vs/editor/editor.main'], function() {
    editor = monaco.editor.create(document.getElementById('editor-html'), {
      language: 'html',
      theme: 'vs-dark',
      minimap: {
        enabled: false
      },
      value: document.getElementById('user-form').innerHTML
    })
  })
}).on('click', '.delete-field', function() {
  $('.edit-properties').data('editing-element').remove()
  $('.edit-properties').empty()
  $('.delete-field-trigger').addClass('d-none')
})
$('.edit-properties').on('input change', function (e) {
  let vals = {}
  $(':input', this).each(function () { vals[this.id] = this.value })
  var $el = $(this).data('editing-element')
  var field = $(e.target).parents('.form-element').data('field')
  // console.log("...", field, template[field])
  $el.html(template[field](vals))
    .data('vals', vals)
})
