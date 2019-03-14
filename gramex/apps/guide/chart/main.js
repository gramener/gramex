/* globals template_data, Promise, vega, array_Object_keys, slug, vegaEmbed, Papa, g1 */
var specName = window.location.href.split('chart=')[1].split('#')[0]
// Refactor: These three global variables exist because
// I haven't yet figured out how to compose event listeners
var dataset_url,
    templates,
    process_state = {}

// dangling state TODO: refactor to inside actions
$('.code div').show()
// $('#prop-editor').hide()

var view, json_file_spec
var model = {
  vega_spec: null,
  form_spec: null,
  mapper: null,
  example_spec_url_data: undefined,
  data_mapper: null
}

var time = {
  history: [],
  pos: 0
}

function templatize_gallery_json(res) {
  var templatized_res = _.template(JSON.stringify(res))({
    // absolute_url: location.href.split('chart')[0]
    absolute_url:
      location.origin +
      location.pathname.slice(0, location.pathname.lastIndexOf('/')) +
      '/'
  })

  return Promise.resolve(JSON.parse(templatized_res))
}

Promise.all([
  vega.loader().load('assets/specs/' + specName + '.vg.json'),
  fetch('examples.json')
    .then(function(res) {
      return res.json()
    })
    .then(templatize_gallery_json)
    .then(function(res) {
      var examples_json_chart = res.filter(function(item) {
        return item.chart == specName
      })

      $('.heading').html(examples_json_chart[0].title)

      examples_json_chart.map(function(item) {
        return item.dataset_url
      })

      // for (var key in examples_json_chart[0].data_mapper) {
      //   mapper[examples_json_chart[0].data_mapper[key]] = examples_json_chart[0].data_mapper[key]
      // }

      model.data_mapper = examples_json_chart[0].data_mapper
      model.mapper = _.mapKeys(model.data_mapper, function(value) {
        return value
      })

      return Promise.resolve(examples_json_chart[0])
    })
])
  .then(drawCopyPasteBlock)
  .catch(function(error) {
    console.log(error) // eslint-disable-line no-console
  })

function renderChart(spec, options, callback) {
  if (options && options.timeTravel) {
    var timeTravel = options.timeTravel
    delete options.timeTravel
  }
  options = Object.assign({}, options, {
    defaultStyle: true,
    renderer: 'svg',
    runAsync: true
  })

  renderCopyPasteBlock(spec)
  vegaEmbed('#chart', spec, options)
    .then(function(result) {
      $('.vega-actions-wrapper')
        .not(':first')
        .remove()
      if (callback) callback(result)
      view = result.view
      if (!timeTravel) {
        time.history.push(_.cloneDeep(model))
      }
      // renderCanvas(view)
    })
    .catch(console.error) // eslint-disable-line no-console
}

function get_vega_spec_id(obj) {
  var vega_spec_ids = []
  function jsonPathTraversor(obj, current_path) {
    if (typeof obj !== 'object') {
      // leaf node
      vega_spec_ids.push(current_path)
    } else {
      if (Array.isArray(obj)) {
        obj.map(function(item, index) {
          jsonPathTraversor(obj[index], current_path + '.' + index)
        })
      } else {
        Object.keys(obj).map(function(item) {
          jsonPathTraversor(obj[item], current_path + '.' + item)
        })
      }
    }
  }
  jsonPathTraversor(obj.marks, 'marks')
  jsonPathTraversor(obj.title, 'title')
  jsonPathTraversor(obj.axes, 'axes')
  vega_spec_ids = vega_spec_ids.concat([
    'width',
    'height',
    'padding',
    'padding.top',
    'padding.left',
    'autosize'
  ])
  return vega_spec_ids
}

$('body').on('change input', '#customize_chart', function(event) {
  if (event.target.dataset['delete']) {
    event.target.dataset['delete'].split('@').map(function(del_prop) {
      _.unset(
        model.vega_spec,
        event.target.dataset['path']
          .split('.')
          .slice(0, -1)
          .join('.') +
          '.' +
          del_prop
      )
    })
  }

  if (!event.target.dataset['path'].endsWith('$')) {
    _.set(
      model.vega_spec,
      event.target.dataset['path'].split('.'),
      event.target.type === 'number' || event.target.type === 'range'
        ? parseFloat(event.target.value)
        : event.target.value
    )
  }

  if (event.type == 'change') {
    renderChart(model.vega_spec)
  }
})

function chartDidRender() {
  // if base already rendered, only rerender customizechart tab-content
  if (templates) {
    $('#customize_chart').html(
      _.template(templates.customize_chart)({
        templates: templates,
        data: template_data(model.vega_spec, view)
      })
    )
    form_default_setter()
    // renderChart(model.vega_spec)

    time.pos++
    return
  }

  var template_urls = [
    './templates/main.template.html',
    './templates/stages.template.html',
    './templates/data_loader.template.html',
    './templates/data_mapper.template.html',
    './templates/customize_chart.template.html',
    './templates/publish_embed.template.html',
    './templates/layer_list.template.html',
    './templates/property_list.template.html',
    './templates/property_detail.template.html',
    './templates/input.template.html',
    './templates/mark.template.html',
    './templates/select.template.html',
    './templates/color_schemes.template.html',
    './templates/padding.template.html',
    './templates/tooltip.template.html',
    './templates/external_url.template.html'
  ]

  Promise.all(
    template_urls.map(function(url) {
      return fetch(url)
    })
  )
    .then(function(responses) {
      return Promise.all(
        responses.map(function(res) {
          return res.text()
        })
      )
    })
    .then(function(tmpls) {
      templates = tmpls.reduce(function(acc, curr, index) {
        acc[
          template_urls[index]
            .split('.template.html')[0]
            .split('./templates/')[1]
        ] = curr
        return acc
      }, {})

      $('#prop-editor').html(
        _.template(templates.main)({
          templates: templates,
          data: template_data(model.vega_spec, view)
        })
      )
    })
}

$('body')
.on('click', '.render-chart', function() {
  if ($(this).text() == 'Render Chart') {
    $(this).text('Customize Chart')
    $('.copy').prop('disabled', false)

    $('#data-viewer').hide()
    $('#prop-editor').hide()
  } else {
    $('#data-viewer').show()
    $('#prop-editor').show()

    $(this).text('Render Chart')
    $('.copy').prop('disabled', true)
  }
})
.on('shown.bs.tab', '#stages a[data-toggle="tab"]', function(e) {
  $('h6', $(e.relatedTarget))
    .removeClass('arrow-info')
    .addClass('arrow-light')
  // $(e.relatedTarget).closest('li').css('pointer-events', 'none')
  $('h6', $(e.target))
    .removeClass('arrow-light')
    .addClass('arrow-info')
})

function form_default_setter(remove_this_bad_arg) {
  var vega_spec_ids = get_vega_spec_id(model.vega_spec)
  // initialize form with spec values
  vega_spec_ids.map(function(vega_spec_id) {
    if ($('[data-path="' + vega_spec_id + '"]').length >= 1) {
      var bad_variable = $('[data-path="' + vega_spec_id + '"]').val(
        _.get(model.vega_spec, vega_spec_id.split('.'))
      )

      if (remove_this_bad_arg !== 'undo') {
        bad_variable.trigger('input')
      }
    }
  })
  renderChart(model.vega_spec)
}

function drawCopyPasteBlock(response) {
  json_file_spec = response[0]
  dataset_url = response[1].dataset_url
  if (!response[1].data_mapper) $('.render-chart').remove()

  // modify relative to absolute urls
  var spec = _.template(json_file_spec)({
    dataset_url: dataset_url,
    data_mapper: response[1].data_mapper
  })

  var parsed_spec = JSON.parse(spec)

  model.vega_spec = parsed_spec
  renderChart(parsed_spec, {}, function(result) {
    setTimeout(function() {
      window.renderComplete = true
    }, 25000)
    view = result.view
    chartDidRender()
    time.pos++
  })
}

var copy_file_string
function renderCopyPasteBlock(spec) {
  var copy_code_file = 'copy_example_vg.html'
  if (copy_file_string) {
    $('.code pre').html(
      _.template(copy_file_string)({ spec: JSON.stringify(spec, null, 2) })
    )
    return
  }
  fetch(copy_code_file)
    .then(function(res) {
      return res.text()
    })
    .then(function(copy_file_string) {
      $('.code pre').html(
        _.template(copy_file_string)({ spec: JSON.stringify(spec, null, 2) })
      )
    })
}

/////////////////////////////////////////////////
/////////////////////////////////////////////////
///////////// EVENT LISTENERS ///////////////////
/////////////////////////////////////////////////
/////////////////////////////////////////////////

$('body')
  .on('click', '.undo', function() {
    if (time.pos == 0) {
      // disable undo button
      $('.undo').removeClass('cursor-pointer')
      return
    }
    if (!$('.undo').hasClass('cursor-pointer')) {
      $('.undo').addClass('cursor-pointer')
    }
    model.vega_spec = _.cloneDeep(time.history[time.pos - 1].vega_spec)
    time.pos--
    form_default_setter('undo')
    renderChart(model.vega_spec, { timeTravel: true })
  })
  .on('click', '.redo', function() {
    if (time.pos == time.history.length) {
      // disable redo button
      $('.redo').removeClass('cursor-pointer')
      return
    }
    if (!$('.redo').hasClass('cursor-pointer')) {
      $('.redo').addClass('cursor-pointer')
    }
    time.pos++
    model.vega_spec = _.cloneDeep(time.history[time.pos - 1].vega_spec)
    form_default_setter('undo')
    renderChart(model.vega_spec, { timeTravel: true })
  })
  .on('click', '.dataloader-next', function() {
    if (process_state.data_mapper) {
      on_cols_fetch(process_state.data_mapper.args, true)
      // $('[href="#data_mapper"]').click()
      $('[href="#data_mapper"]').tab('show')
    } else {
      $('.loader').removeClass('d-none')
      fetch(model.vega_spec.data[0].url)
        .then(function(res) {
          return res.json()
        })
        .then(function(res) {
          $('.loader').addClass('d-none')
          model.example_spec_url_data = res
          on_cols_fetch(res, true)
          // $('[href="#data_mapper"]').click()
          $('[href="#data_mapper"]').tab('show')
        })
    }
  })
  .on('click', '[href="#data_mapper"]', function() {
    if (process_state.data_mapper) {
      on_cols_fetch(process_state.data_mapper.args, false)
    } else {
      if (model.example_spec_url_data) {
        on_cols_fetch(model.example_spec_url_data, false)
        return
      }
      $('.loader').removeClass('d-none')
      fetch(model.vega_spec.data[0].url)
        .then(function(res) {
          return res.json()
        })
        .then(function(res) {
          model.example_spec_url_data = res
          on_cols_fetch(res, true)
          $('.loader').addClass('d-none')
        })
    }
  })
  .on('click', '.datamapper-next', function() {
    $('a[href="#customize_chart"]').click()
  })
  .on('click', 'a[href="#customize_chart"]', function() {
    drawCopyPasteBlock([
      json_file_spec,
      { data_mapper: model.data_mapper, dataset_url: dataset_url }
    ])
  })
  .on('change', '.fh-url', function() {
    dataset_url = $('.fh-url').val()

    $('.loader').addClass('d-none')
    fetch(dataset_url)
      .then(function(res) {
        return res.json()
      })
      .then(function(res) {
        $('.loader').addClass('d-none')
        process_state['data_mapper'] = {
          function: 'on_cols_fetch',
          args: res
        }
        on_cols_fetch(res, true)
        process_state['data_mapper'] = {
          function: 'on_cols_fetch',
          args: res
        }
        // $('[href="#data_mapper"]').click()
        // $('[href="#data_mapper"]').tab('show')
      })

    // TODO: validate url
  })
  .on('change', '#csv-file-input', function(event) {
    event.stopPropagation()

    $('li .nav-item').closest()
    var csv_contents

    Promise.all([
      getFileContent(event.target.files[0]),
      fetch(model.vega_spec.data[0].url)
    ])
      .then(function(responses) {
        return Promise.all([Promise.resolve(responses[0]), responses[1].json()])
      })
      .then(function(res) {
        csv_contents = res[0]
        var csv_contents_converted = Papa.parse(csv_contents, {
          header: true,
          skipEmptyLines: true,
          dynamicTyping: true
        }).data
        $('.fh-table').formhandler({
          data: csv_contents_converted,
          pageSize: 5,
          export: false
        })
        // dangerous mutation stuff below
        var parsed_json_file_spec = JSON.parse(json_file_spec)
        delete parsed_json_file_spec.data[0].url
        parsed_json_file_spec.data[0].values = csv_contents_converted
        json_file_spec = JSON.stringify(parsed_json_file_spec, null, 2)
        on_cols_fetch(csv_contents_converted, true)
        process_state['data_mapper'] = {
          function: 'on_cols_fetch',
          args: csv_contents_converted
        }
      })
  })
  .on('click', '.publish', function() {
    // generate unique url for current spec
    // POST request to formhandler URL
    $.post(
      '_chartogram/',
      JSON.stringify({
        chartname: specName,
        spec: model.vega_spec
      }),
      function(response) {
        // create an URL with response.id
        var link =
          window.location.origin +
          location.pathname.slice(0, location.pathname.lastIndexOf('/')) +
          '/' +
          '_chartogram/' +
          response.chart.id
        $('.share-url').html(link)
        $('.share-url').attr('href', link)
      },
      'json'
    )
  })

function getFileContent(file) {
  return new Promise(function(resolve) {
    var fr = new FileReader()
    fr.onload = function() {
      resolve(fr.result)
    }
    fr.readAsText(file)
  })
}

function on_cols_fetch(fh_dataset, from_data_loader) {
  // state storage of res

  // RENDER DATA-MAPPER dropdowns with fh_col_names
  if (from_data_loader)
    $('#data_mapper').html(
      _.template(templates['data_mapper'])({
        templates: templates,
        fh_col_names: array_Object_keys(fh_dataset),
        data_mapper: model.data_mapper
      })
    )
}

$('body').on('change', '.mapper-table', function() {
  for (var key in model.data_mapper) {
    model.data_mapper[key] = $('#map-' + slug(key)).val()
  }
})

$('body').on('click', '.palette', function(event) {
  var scheme_name = $(this).attr('title')
  var palette_html = $('.palette[title=' + scheme_name + ']').html()
  $('.color .dropdown-toggle').empty()
  $('.color .dropdown-toggle').append(
    '<div class="sel_palette d-flex d-inline-flex" title=' +
      $(this).attr('title') +
      '></div>'
  )
  $('.sel_palette').append(palette_html)
  var scale_prop_path = $(this).attr('data-path')
  var prop_field_path =
    scale_prop_path
      .split('.')
      .slice(0, -1)
      .join('.') + '.field'
  var selected_field = $('#' + prop_field_path.split('.').join('-')).val()
  var scale_type = get_scale_type(_.get(model.vega_spec, prop_field_path))
  // console.log("scale type: ", scale_type)
  // set this mark's attribute to have this new scale
  _.set(model.vega_spec, scale_prop_path, scale_prop_path)

  var scale_obj_index = _.findIndex(model.vega_spec.scales, [
    'name',
    scale_prop_path
  ])
  var scale_obj = model.vega_spec.scales[scale_obj_index]

  // create a new scale for this particular marktype_color_scale
  if (scale_obj_index > -1) {
    // scale already defined for this scale, update only "range"
    scale_obj.name = scale_prop_path
    scale_obj.type = scale_type
    scale_obj.domain = {
      data: model.vega_spec.data[0].name,
      field: selected_field
    }
    scale_obj.range = {
      scheme: $(event.currentTarget).attr('title')
    }
  } else {
    // create new scale
    var new_scale = {}
    new_scale.name = scale_prop_path
    new_scale.type = scale_type
    new_scale.domain = {
      data: model.vega_spec.data[0].name,
      field: selected_field
    }
    new_scale.range = {
      scheme: $(event.currentTarget).attr('title')
    }
    model.vega_spec.scales.push(new_scale)
  }

  // trigger 'change' event aftert setting the value
  $(event.currentTarget).val($(event.currentTarget).attr('data-path'))
  $(event.currentTarget).change()
})

function get_scale_type(col_name) {
  var types = g1.types(view.data(model.vega_spec.data[0].name), {
    convert: true
  })
  if (types[col_name] == 'number') return 'sequential'
  else if (types[col_name] == 'string') return 'ordinal'
  else if (types[col_name] == 'date') return 'time'
}

$('.copy')
  .tooltip({ trigger: 'click' })
  .on('click', function() {
    var $textarea = $('<textarea></textarea>')
      .val($('.code pre').text())
      .appendTo(document.body)
      .select()
    document.execCommand('copy')
    $textarea.remove()
    // After some time, hide the tooltip
    setTimeout(function() {
      $('.copy').tooltip('hide')
    }, 1000)
  })

$('body').on('click', '.download-sample', function() {
  $.get(model.vega_spec.data[0].url).done(function(res) {
    var csv = Papa.unparse(res)
    downloadString(csv, 'text/csv', specName + '.csv')
  })
})

function downloadString(text, fileType, fileName) {
  var blob = new Blob([text], { type: fileType })

  var a = document.createElement('a')
  a.download = fileName
  a.href = URL.createObjectURL(blob)
  a.dataset.downloadurl = [fileType, a.download, a.href].join(':')
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(function() {
    URL.revokeObjectURL(a.href)
  }, 1500)
}
