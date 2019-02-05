/* exported template_data */
/* globals type_mapper */

var scales_list
var data_columns = { 'empty': [] }


function template_data(vega_spec, view) {
  var data = {}

  scales_list = vega_spec.scales.map(function (scale) {
    return scale.name
  })

  data_columns = vega_spec.data
    .reduce(function (accumulator, current) {
      accumulator[current.name] = array_Object_keys(view.data(current.name))
      return accumulator
    }, {})

  data['layer_list'] = [
    {
      name: 'chart'
    }
  ]

  data['property_list'] = {
    chart: [
      {
        title: 'Width',
        id: 'g-width'.replace('.', '-'),
        template: 'input',
        detail: {
          id: 'g-width'.replace('.', '-'),
          input: 'number',
          label: 'Width',
          unit: 'px',
          attrs: {
            'data-path': 'width',
            value: 600,
            min: 0,
            max: 10000,
            step: 1
          }
        }
      },
      {
        title: 'Height',
        template: 'input',
        id: 'g-height'.replace('.', '-'),
        detail: {
          id: 'g-height'.replace('.', '-'),
          input: 'number',
          label: 'Height',
          unit: 'px',
          attrs: {
            value: 360,
            'data-path': 'height',
            min: 0,
            max: 10000,
            step: 1
          }
        }
      }
    ]
  }

  if (!vega_spec.title) {
    vega_spec.title = {
      'text': 'Chart title',
      'anchor': 'start',
      'color': '#485465',
      'fontSize': 16,
      'fontWeight': 900,
      'font': 'Roboto'
    }
  }
  data['layer_list'].push({ name: 'title' })
  data['property_list']['title'] = title_marshal(vega_spec.title)

  if (vega_spec.marks[0].type == 'group') {
    mark_iterator(vega_spec.marks[0].marks, 'marks.0.')
  } else {
    mark_iterator(vega_spec.marks, '')
  }

  function mark_iterator(mark_array, group_prefix) {
    mark_array.map(function (mark, index) {
      var mark_name = mark.name || mark.type + ' ' + index
      data['layer_list'].push({ name: slug(mark_name) })
      data['property_list'][slug(mark_name)] = mark_marshal(mark_array[index], index, group_prefix)
    })
  }

  return data
}

function title_marshal(title) {
  var title_template_data = Object.keys(title).map(function (title_prop) {
    var title_data = {
      title: title_prop,
      id: ('title.' + title_prop).replace('.', '-'),
      template: getTemplateType(title_prop, 'value'),
      detail: {
        options: getOptions(title_prop, 'value'),
        id: ('title.' + title_prop).replace('.', '-'),
        input: getInputType(title_prop, 'value'),
        label: title_prop,
        unit: getUnit(title_prop)
      }
    }

    title_data.detail.attrs = {
      'data-path': 'title.' + title_prop
    }
    title_data.detail.attrs = Object.assign(title_data.detail.attrs, getAttrs(title_prop))
    return title_data
  })


  return title_template_data
}

function mark_marshal(mark, index, group_prefix) {
  group_prefix = group_prefix || ''
  // get_data_view(mark.data)

  // all enter encodes must be re-changed to update by default
  // BAD SIDE EFFECT CODE
  if (mark.encode.enter) {
    mark.encode.update = _.merge(mark.encode.update, mark.encode.enter)
    delete mark.encode.enter
  }

  var mark_template_data = Object.keys(mark.encode.update).map(function (key) {
    var things = ['value', 'field', 'scale', 'signal']


    var details = things.map(function (thing) {

      // if (scale || field) then return two objects (one for each)
      var mark_data = 'from' in mark ? mark.from.data : 'empty'

      var _mark_return_obj = {
        template: getTemplateType(key, thing),
        input: getInputType(key, thing),
        options: getOptions(key, thing, mark_data),
        label: getValueLabel(key, thing),
        id: (group_prefix + 'marks.' + index + '.encode.update.' + key + '.' + thing).split('.').join('-'),
        unit: getUnit(key),
        attrs: {
          'data-path': (group_prefix + 'marks.' + index + '.encode.update.' + key + '.' + thing),
          'data-delete': getDeleteAttr(key, thing)
        }
      }
      _mark_return_obj.attrs = Object.assign(_mark_return_obj.attrs, getAttrs(key))

      return _mark_return_obj
    })

    return {
      title: titleMap(key),
      template: 'mark',
      id: (group_prefix + 'marks.' + index + '.encode.update.' + key).split('.').join('-'),
      detail: details
    }
  })

  return mark_template_data
}

var getDeleteAttr = function (prop, value_type) {
  /* Sometimes, when signal is applied, we still need to apply scale
    Value logic is fine = delete signal, field, scale
    Field is fine, but do we need to retain scale on change of field?
  */
  if (value_type == 'signal') {
    return 'value@field@scale'
  }

  if (value_type == 'value') {
    return 'signal@field@scale'
  }

  if (value_type == 'field') {
    return 'signal@value'
  }
  return ''
}

function getTemplateType(prop, value_type) {
  if (value_type == 'value' &&
      _.isObject(type_mapper[prop]) &&
      type_mapper[prop]['type'] == 'select'
  ) {
    return 'select'
  }

  if (value_type == 'scale' && type_mapper[prop] == 'Color') {
    return 'color_schemes'
  }

  if (value_type == 'field' || value_type == 'scale') {
    return 'select'
  }

  return 'input'
}

function getInputType(prop, value_type) {

  if (value_type == 'signal') {
    return 'text'
  } else if (value_type == 'value') {
    return _.isObject(type_mapper[prop]) ? type_mapper[prop].type : type_mapper[prop].toLowerCase()
  }

  return ''
}

function getOptions(prop, value_type, dataset_name) {
  if (value_type == 'scale') {
    return scales_list
  }

  if (value_type == 'field') {
    return data_columns[dataset_name]
  }

  if (value_type == 'value') {
    // because getOptions gets called only for existing enum types
    return type_mapper[prop]['values']
  }

}


var titleMap = function (key) {
  return key[0].toUpperCase() + key.slice(1)
}

var getValueLabel = function (prop, value_type) {
  if (value_type == 'value') {
    return 'Select a ' + (_.isObject(type_mapper[prop]) ? 'value' : type_mapper[prop].toLowerCase())
  }
  if (value_type == 'field') {
    return 'Data column'
  }

  if (value_type == 'scale') {
    // TODO: if color, in dropdown disable non-color ranges
    if (type_mapper[prop] == 'Color') {
      return 'Palette'
    }
    return 'Map to range'
  }

  if (value_type == 'signal') {
    return 'Apply data conditions'
  }
}

function getAttrs(prop) {
  return type_mapper[prop].attrs ? type_mapper[prop].attrs : {}
}

var getUnit = function (key) {
  var unitMapper = {
    color: 'hex',
    number: 'px'
  }
  return key in unitMapper ? unitMapper[key] : null
}

///////////////////////////////
////// Helper Functions ///////
///////////////////////////////

function slug(text) {
  return text.toString().toLowerCase()
    .replace(/\s+/g, '-')           // Replace spaces with -
    .replace(/[^\w\\-]+/g, '')      // Remove all non-word chars
    .replace(/\\-\\-+/g, '-')       // Replace multiple - with single -
    .replace(/^-+/, '')             // Trim - from start of text
    .replace(/-+$/, '')            // Trim - from end of text
}

function array_Object_keys(arr) {
  var headers = []
  arr.map(function (obj) {
    Object.keys(obj).map(function (key) {
      if (headers.indexOf(key) < 0) {
        headers.push(key)
      }
    })
  })
  return headers
}
