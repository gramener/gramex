/*global config, $, vega, vegam, moment, g1, vegaTooltip, vl,
console, location */
/* exported updateParams, vegamDraw, unitDraw, filterTime, filterSelect,
drawFilters drawViz, updateView */

function updateParams(params, keeponly, remove) {
  var query = g1.url.parse(params)
  keeponly = keeponly || []
  remove = remove || []
  if (keeponly.length) {
    var to_remove = Object.keys(query.searchKey).filter(function(i) {
      // remove filter-like characters from end
      var ci = i.replace(/(>~|<~|!~|>|<|~|!)$/, '')
      return keeponly.indexOf(ci) === -1
    })
    remove.push.apply(remove, to_remove)
  }
  if (remove.length) {
    var update = {}
    remove.forEach(function(k) {
      update[k] = null
    })
    query.update(update)
  }
  return query.toString()
}

function vegamDraw(s, on) {
  s.spec.width = $(on).width()
  s.spec.height = 250
  // need vega spec to alter
  var vspec = vl.compile(s.spec).spec
  // remove tooltip for certain mark types
  vspec.marks.forEach(function(m) {
    if (['line', 'area'].indexOf(m.type) > -1) {
      m.interactive = false
    }
  })
  var view = new vega.View(vega.parse(vspec))
    .renderer('svg')
    .initialize(on)
    .hover()
    .run()
  view.addEventListener('click', function(event, item) {
    console.log('CLICK', event, item)   // eslint-disable-line no-console
    if (typeof item !== 'undefined' && item.hasOwnProperty('datum')) {
      console.log(item.datum)   // eslint-disable-line no-console
    }
  })
  vegaTooltip.vegaLite(view, s.spec)
}

function unitDraw(o, on, formatter) {
  formatter = formatter || ''
  $(on).html(formatter(o[0].value))
}

function filterTime(start, end, on) {
  $(on).daterangepicker({
    startDate: new Date(start),
    endDate: new Date(end),
    locale:{format: 'MMM D, YYYY'},
    ranges: {
      'Today': [moment(), moment()],
      'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
      'Last 7 Days': [moment().subtract(6, 'days'), moment()],
      'Last 30 Days': [moment().subtract(29, 'days'), moment()],
      'This Month': [moment().startOf('month'), moment().endOf('month')],
      'Last Month': [moment().subtract(1, 'month').startOf('month'),
        moment().subtract(1, 'month').endOf('month')]
    }
  })
}

function filterSelect(values, key, on) {
  var output = []
  $.each(values, function(k, v) {
    output.push('<option value="'+ v[key] +'">'+ v[key] +'</option>')
  })
  var el = $(on)
  el.append(output.join(''))
  return el
}

function drawFilters(params) {
  var query = g1.url.parse(params)
  var config_filter = config.filters
  $.each(config_filter, function(k, spec) {
    if (spec.type == 'select') {
      $.getJSON(spec.url)
        .done(function(data) {
          var el = filterSelect(data, spec.column, spec.el)
          el.promise().done(function(){
            el.selectpicker({style: 'btn-info btn-sm'})
            if (query.searchKey[spec.column]) {
              setSelectFilter(el, query.searchKey[spec.column])
            }
          })
        })
    } else if (spec.type == 'daterange') {
      setDatefilter(spec, query)
    } else {
      console.warn('unsupported filter type')  // eslint-disable-line no-console
    }
  })
}

function setFilters(params) {
  var query = g1.url.parse(params)
  var config_filter = config.filters
  $.each(config_filter, function(k, spec) {
    if (spec.type == 'select') {
      if (query.searchKey[spec.column]) {
        setSelectFilter($(spec.el), query.searchKey[spec.column])
      }
    } else if (spec.type == 'daterange') {
      setDatefilter(spec, query)
    }
  })
}

function setDatefilter(spec, query) {
  var start = query.searchKey[spec.column + '>~'].substring(0, 10)
  var end = query.searchKey[spec.column + '<~'].substring(0, 10)
  start = start || moment().subtract(29, 'days')
  end = end || moment()
  filterTime(start, end, spec.el)
}

function setSelectFilter(el, value) {
  el.selectpicker('val', value)
}

function viewOn(conf) {
  return $.ajax({
    url: conf.url,
    beforeSend: function() {
      this.conf = conf
      var loading = conf.loading || '<i class="fa fa-spin fa-spinner"></i>'
      $(conf.on).html(loading)
    }
  })
}

function drawViz(params) {
  config.viewsConfig.forEach(function(spec) {
    viewOn({
      url: spec.url + updateParams(params, spec.keep || []),
      on: spec.on})
      .done(function(data) {
        if (data.length == 0) {
          $(this.conf.on).html('[ No Data ]')
          return
        }
        if (spec.type === 'viz') {
          spec.viz[0]['data'] = data
          var vm = vegam.vegam().fromjson(spec.viz)
          vegamDraw(vm, this.conf.on)
        } else if (spec.type === 'kpi') {
          unitDraw(data, this.conf.on, spec.formatter)
        }
      })
      .fail(function(xhr) {
        console.error({'on': this.conf.on, 'error': xhr.statusText})  // eslint-disable-line no-console
        $(this.conf.on).html('[ error ]')
      })
  })
}

function updateView() {
  var params = g1.url.parse(location.search)
  setFilters(params)
  drawViz(params)
}
