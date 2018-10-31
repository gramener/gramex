/* exported draw_table, create_dropdowns */
/* globals g1 */
function draw_table(url) {
  /**
  * Draws the groupmeans table template
  */
  var param = g1.url.parse(window.location.href).search
  $.getJSON(url + '-groupmeans?' + param).done(function (data) {
    $('#template-table').on('template', function () {
    }).template({ data: data })
  })
}
function create_dropdowns(url) {
  /**
  * Takes an input url, drives the dropdown and form generation.
  */
  $.getJSON(url + '?_limit=20').done(function (data) {
    var types = g1.types(data)
    var cols = _.keys(data[0])
    var metrics = _.filter(cols, function (d) { return types[d] == 'number' })
    $('#groups').dropdown({
      data: cols,
      target: 'pushState',
      multiple: true,
      options: {
        style: 'btn btn-sm',
        noneSelectedText: 'Groups'
      }
    })
    $('#metrics').dropdown({
      data: metrics,
      target: 'pushState',
      multiple: true,
      options: {
        style: 'btn btn-sm',
        noneSelectedText: 'Metrics'
      }
    })
    $('body').urlfilter({
      event: 'submit',
      target: 'pushState',
      remove: true
    })
    $('body').on('submit', '#inputform', function () {
      var keys = {
        '#metrics select': 'numbers',
        '#groups select': 'groups'
      }
      var params = {}
      _.each(['#groups select', '#metrics select'], function (id) {
        var selected = $(id).val()
        params[keys[id]] = selected
      })
      var param = g1.url.parse(window.location.href).update(params)
      history.pushState({}, '', param.toString())
      draw_table(url)
    })
  })
}
