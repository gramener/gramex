/* globals dragula, user, user_name, editor, active_form_id */

const right = '.user-form'
const left = '.drag-fields'
// var editor

$(function () {
  setTimeout(function () {
    dragAndDrop.init()
  }, 300)
}) // anonymous function

let element_data, for_edits
//, current_form_el
let view = 'default'

/* Fetch form fields and their attributes */
fetch('assets/data/input.json')
  .then(response => response.json())
  .then(function(data) {
    element_data = data[0]
    for_edits = JSON.parse(JSON.stringify(element_data))
  })

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
  dropped: function () {
    $('#publish-form').removeClass('d-none')
    $('.btn-link').removeClass('d-none')
  }
};

function render_popover(data) {
  $('.popover-template').template({fields: data.fields, view: view})
}

$('body').on('click', '#user-form input', function () {
  // show options in the third container
  // current_form_el = this
  render_popover(element_data)
}).on('change', '#edit-html input', function() {
  // using an object (element_data) update respective form field in the second container
  const _el = $(this).data('element')
  for_edits.fields[_el].value = $(this).val()
  // render_popover(for_edits)
  $('.input-template').on('template', function() {
    $('#user-form input').html($('input-template').html())
  }).template({data: for_edits.fields[_el]}, {target: '#user-form'})
}).on('click', '#publish-form', function() {
  let $icon = $('<i class="fa fa-spinner fa-2x fa-fw align-middle"></i>').appendTo(this)
  // create a database entry with for_edits
  let _md = {
    name: $('#form-name').val() || 'Untitled',
    categories: [],
    description: $('#form-description').val()
  }
  let form_details = {
    data: {
      config: JSON.stringify(element_data),
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
        form_details.id = response.data.modify.id
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
}).on('shown.bs.tab', 'a[data-toggle="tab"]', function() {
  // on tab change, dragula needs to be reinitialized, e.target.id
  // dragAndDrop.dragula.destroy(); // dragAndDrop.init()
}).on('click', '.btn-link', function() {
  $('.update-form').removeClass('d-none')
  editor.setValue(
    document.getElementById('user-form').innerHTML
  )
}).on('click', '.update-form', function() {
  let $icon = $('<i class="fa fa-spinner fa-2x fa-fw align-middle"></i>').appendTo(this)
  $('#user-form').html(editor.getValue())
  $icon.fadeOut()
})
