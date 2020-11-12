/* globals dragula, user, user_name */

const right = '.user-form'
const left = '.tab-pane'

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
    // this.count++;
    $('#publish-form').removeClass('d-none')
    $('#form-name').removeClass('d-none')
  }
};

function render_popover(data) {
  $('.popover-template').template({fields: data.fields, view: view})
}

$('body').on('click', '#user-form input', function () {
  // show options in the third container
  // current_form_el = this
  render_popover(element_data)
}).on('change', '#element-properties input', function() {
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
    name: $('#form-name').val() || `Untitled`,
    categories: [],
    fields: _.countBy(_.map(element_data.fields, 'type'))
  }
  $.ajax('publish', {
    method: 'POST',
    data: {
      config: JSON.stringify(element_data),
      html: $('#user-form form').html(),
      metadata: JSON.stringify(_md),
      user: user
    },
    success: function (response) {
      $('.post-publish').removeClass('d-none')
      $('.form-link').html(`<a href="form/${response.data.modify.id}">View form</a>`)
    },
    error: function () { },
    complete: function() { $icon.fadeOut() }
  })
}).on('shown.bs.tab', 'a[data-toggle="tab"]', function() {
  // on tab change, dragula needs to be reinitialized, e.target.id
  // dragAndDrop.dragula.destroy(); // dragAndDrop.init()
})
