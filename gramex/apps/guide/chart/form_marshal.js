/* exported template_data */
/* globals type_mapper */

function slug(text) {
  return text.toString().toLowerCase()
    .replace(/\s+/g, '-')           // Replace spaces with -
    .replace(/[^\w\\-]+/g, '')      // Remove all non-word chars
    .replace(/\\-\\-+/g, '-')       // Replace multiple - with single -
    .replace(/^-+/, '')             // Trim - from start of text
    .replace(/-+$/, '')            // Trim - from end of text
}

function Array_Object_keys(arr) {
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


// function data_mapper() {

//   // event listener for data_mapper interface
//   ///////////////////////////////////////////
//   //// Gallery Columns //// App Columns /////
//   ///////////////////////////////////////////
//   ////     Label      ////    Month   ▼  ////
//   ////     Count      ////  Frequency ▼  ////
//   ///////////////////////////////////////////

//   return {
//     label: 'month',
//     count: 'frequency'
//   }
// }


var scales_list
var data_columns = {'empty': []}


function template_data(vega_spec, view) {
  var data = {}

  scales_list = vega_spec.scales.map(function (scale) {
    return scale.name
  })

  data_columns = vega_spec.data
    .reduce(function (accumulator, current) {
      accumulator[current.name] = Array_Object_keys(view.data(current.name))
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
    ],
  }

  vega_spec.marks.map(function (mark, index) {
    var mark_name = mark.name || mark.type + ' ' + index
    data['layer_list'].push({ name: slug(mark_name) })
    data['property_list'][slug(mark_name)] = mark_marshal(vega_spec.marks[index], index)
  })

  return data
}



function mark_marshal(mark, index) {
  // get_data_view(mark.data)
  if (!mark.encode) return []          // group marks dont have encode
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

      return {
        template: getTemplateType(key, thing),
        input: getInputType(key, thing),
        options: getOptions(key, thing, mark_data),
        label: getValueLabel(key, thing),
        id: ('marks.' + index + '.encode.update.' + key + '.' + thing).split('.').join('-'),
        unit: getUnit(key, thing),
        attrs: {
          'data-path': ('marks.' + index + '.encode.update.' + key + '.' + thing),
          'data-delete': getDeleteAttr(key, thing)
        }
      }
    })

    return {
      title: titleMap(key),
      template: 'mark',
      id: ('marks.' + index + '.encode.update.' + key).split('.').join('-'),
      detail: details
    }
  })

  return mark_template_data
}





var getDeleteAttr = function (prop, value_type) {
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
  if (value_type == 'field' || value_type == 'scale') {
    return 'select'
  }
  return 'input'
}

function getInputType(prop, value_type) {
  if (value_type == 'value') {
    return type_mapper[prop].toLowerCase()
  }

  if (value_type == 'signal') {
    return 'text'
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

}


var titleMap = function (key) {
  return key[0].toUpperCase() + key.slice(1)
}

var getValueLabel = function (prop, value_type) {
  if (value_type == 'value') {
    return 'Select single ' + type_mapper[prop].toLowerCase()
  }
  if (value_type == 'field') {
    if (type_mapper[prop] == 'Color') {
      return 'Color using column'
    }
    return 'Select column'
  }
  if (value_type == 'scale') {
    // TODO: if color, in dropdown disable non-color ranges
    if (type_mapper[prop] == 'Color') {
      return 'Palette'
    }
    return 'Range map selected column'
  }

  if (value_type == 'signal') {
    return 'Apply data conditions'
  }

}

var getUnit = function (key) {
  var unitMapper = {
    color: 'hex',
    number: 'px'
  }
  return key in unitMapper ? unitMapper[key] : null
}
