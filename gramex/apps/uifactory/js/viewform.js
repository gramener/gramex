/* globals form_id, current_form_id, initiate_copy, hljs */

// use the snippets config to render the form using user-created form config
$('.btn.viewsource').addClass('d-none')
$.ajax(`../embed/${form_id}.json`, {
  success: function(_form_config) {
    _.each(_form_config, function(opts) {
      let dir = opts.component
      if(dir === 'bs4-html') {
        opts.value = opts.value.replace(/\\n/g, "<br>")
      }
      $(`<${dir}></${dir}>`)
        .appendTo('#view-form form')
        .attr(opts)
    })
    hljs.highlightAll()
  }
})
$('svg').urlfilter({target: '#'})

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
  // convert array of objects to object
  let field_vals_obj = {}
  _.each(field_vals, function(item) {
    for(let key in item) {
      field_vals_obj[key] = item[key]
    }
  })

  $.ajax(`../analytics/?db=${form_id}&form_id=${form_id}&response=${encodeURIComponent(JSON.stringify(field_vals_obj))}`, {
    method: 'POST',
    success: function() {
      // submit another record
      $('#view-form').addClass('d-none')
      $('.post-submission').removeClass('d-none')
      $('.toast-body').html('Your response has been recorded.')
      $('.toast').toast('show')
    },
    complete: function() { $icon.fadeOut() }
  })
}).on('click', '[data-formaction]', function() {
  if($(this).data('formaction') === 'copy')
    initiate_copy('..', form_id)
})
