/*global config, $, vegam, d3, moment, g1, vegaTooltip, vegaEmbed, vl,
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
  var opts = {
    actions: {export: false, source: false, editor: false},
    renderer: 'svg'}
  var autosize = {
    type: 'fit',
    contains: 'padding'
  }
  s.spec.autosize = autosize
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
  vegaEmbed(on, vspec, opts).then(function(r) {
    vegaTooltip.vegaLite(r.view, s.spec)
    r.view.addEventListener('click', function(event, item) {
      console.log('CLICK', event, item)   // eslint-disable-line no-console
      if (typeof item !== 'undefined' && item.hasOwnProperty('datum')) {
        console.log(item.datum)   // eslint-disable-line no-console
      }
    })
  }).catch(console.error)   // eslint-disable-line no-console
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
  el.find('option[value="' + value + '"]').prop('selected', true)
}

function drawViz(params) {
  // KPIS
  $.getJSON('query/aggD/kpi-pageviews/' + updateParams(params))
  .done(function(data) {
    unitDraw(data, '.kpi-pageviews', d3.format(',.2d'))
  })
  $.getJSON('query/aggD/kpi-sessions/' + updateParams(params, ['user.id', 'time']))
  .done(function(data) {
    unitDraw(data, '.kpi-sessions', d3.format(',.2d'))
  })
  $.getJSON('query/aggD/kpi-users/' + updateParams(params))
  .done(function(data) {
    unitDraw(data, '.kpi-users', d3.format(',.2d'))
  })
  $.getJSON('query/aggD/kpi-avgtimespent/' + updateParams(params, ['user.id', 'time']))
  .done(function(data) {
    unitDraw(data, '.kpi-avgtimespent', (function(v){ return d3.format(',.1f')(v/60) + ' min' }))
  })
  $.getJSON('query/aggD/kpi-urls/' + updateParams(params))
  .done(function(data) {
    unitDraw(data, '.kpi-urls', d3.format(',.2d'))
  })
  $.getJSON('query/aggD/kpi-avgloadtime/' + updateParams(params))
  .done(function(data) {
    unitDraw(data, '.kpi-avgloadtime', (function(v){ return d3.format(',.1f')(v) + ' ms' }))
  })
  // visuals
  $.getJSON('query/aggD/pageviewstrend/' + updateParams(params))
    .done(function(data) {
      var vm = vegam.vegam(data, {types: {time:'date'}})
        .area({x:'time', y:'pageviews', props: {fill:'#c5e5f8'}})
        .line({x:'time', y:'pageviews', props: {stroke:'#186de5'}})
        .scatter({x:'time', y:'pageviews', mark:'circle', props: {fill:'#186de5', size:50}})
        .style({x_axis_format:'%d %b'})
      vegamDraw(vm, '.vegam-pageviewstrend')
    })
  $.getJSON('query/aggD/sessionstrend/' + updateParams(params, ['user.id', 'time']))
    .done(function(data) {
      var vm = vegam.vegam(data, {types: {time:'date'}})
        .area({x:'time', y:'sessions', props: {fill:'#cc95ff'}})
        .line({x:'time', y:'sessions', props: {stroke:'#8f65b5'}})
        .scatter({x:'time', y:'sessions', mark:'circle', props: {fill:'#8f65b5', size:50}})
        .style({x_axis_format:'%d %b'})
      vegamDraw(vm, '.vegam-sessionstrend')
    })
  $.getJSON('query/aggD/toptenuri/' + updateParams(params))
    .done(function(data) {
      var vm = vegam.vegam(data)
        .bar({y:'uri', x:'views', order: 'views', props: {fill:'#77b7f1'}})
        .style({y_sort_op:'sum', y_sort_field:'views', y_sort_order:'descending'})
      vegamDraw(vm, '.vegam-toptenuri')
    })
  $.getJSON('query/aggD/toptenusers/' + updateParams(params))
    .done(function(data) {
      var vm = vegam.vegam(data)
        .bar({y:'[user.id]', x:'views', order: 'views', props: {fill:'#8f65b5'}})
        .style({y_sort_op:'sum', y_sort_field:'views', y_sort_order:'descending'})
      vegamDraw(vm, '.vegam-toptenusers')
    })
  $.getJSON('query/aggD/toptenstatus/' + updateParams(params))
    .done(function(data) {
      var vm = vegam.vegam(data, {types: {status:'string'}})
        .bar({y:'status', x:'views', order: 'views', props: {fill:'#77b7f1'}})
        .style({y_sort_op:'sum', y_sort_field:'views', y_sort_order:'descending'})
      vegamDraw(vm, '.vegam-toptenstatus')
    })
  $.getJSON('query/aggD/toptenip/' + updateParams(params))
    .done(function(data) {
      var vm = vegam.vegam(data)
        .bar({y:'ip', x:'views', order: 'views', props: {fill:'#8f65b5'}})
        .style({y_sort_op:'sum', y_sort_field:'views', y_sort_order:'descending'})
      vegamDraw(vm, '.vegam-toptenip')
    })
  $.getJSON('query/aggD/loadtimetrend/' + updateParams(params))
    .done(function(data) {
      var vm = vegam.vegam(data, {types: {time:'date'}})
        .line({x:'time', y:'loadtime', props: {stroke:'#ff8101'}})
        .scatter({x:'time', y:'loadtime', mark:'circle', props: {fill:'#ff8101', size:50}})
        .style({x_axis_format:'%d %b'})
      vegamDraw(vm, '.vegam-loadtimetrend')
    })
  $.getJSON('query/aggD/loadtimeviewstrend/' + updateParams(params))
    .done(function(data) {
      var vm = vegam.vegam(data, {types: {time:'date'}})
        .area({x:'time', y:'views', props: {fill:'#cc95ff'}})
        .style({y_axis_grid:false}, -1)
        .line({x:'time', y:'views', props: {stroke:'#8f65b5'}})
        .scatter({x:'time', y:'views', mark:'circle', props: {fill:'#8f65b5', size:20}})
        .style({y_axis:null}, -2)
        .line({x:'time', y:'loadtime', props: {stroke:'#ff8101'}})
        .scatter({x:'time', y:'loadtime', mark:'circle', props: {fill:'#ff8101', size:50}})
        .style({y_axis_grid:false}, -2)
        .resolve({scale_y:'independent'})
      vegamDraw(vm, '.vegam-loadtimeviewstrend')
    })
}

function updateView() {
  var params = g1.url.parse(location.search)
  setFilters(params)
  drawViz(params)
}
