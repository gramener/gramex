(function (conf) {
  var script = document.currentScript
  var id = script.getAttribute('data-id') || conf.id || String(Math.random())
  var loading = conf.loading || '<h3>Loading...</h3><i class="fa fa-spin fa-spinner fa-2x"></i>'
  var renderer = conf.renderer || 'svg'
  var spec = conf.spec || {}
  var width = +script.getAttribute('data-width') || spec.width || 400
  var height = +script.getAttribute('data-height') || spec.height || 200
  document.write('<div id="' + id + '" style="text-align:center;width:' + width + 'px;height:' + height + 'px">' + loading + '</div>')
  document.addEventListener('DOMContentLoaded', function () {
    var container = document.getElementById(id)
    try {
      container.spec = {}
      if ('fromjson' in spec) {
        container.spec.vegam = spec.fromjson
        spec = vegam.vegam([]).fromjson(spec.fromjson).spec
      }
      spec.width = width
      spec.height = height
      if (spec['$schema'].endsWith('vega-lite/v2.json')) {
        container.spec.vegalite = spec
        spec = vl.compile(spec).spec
      }
      container.spec.vega = spec
      var view = new vega.View(vega.parse(spec))
        .renderer(renderer)
        .initialize(container)
        .hover()
        .run()
      container.vega = view
    } catch (error) {
      container.innerHTML = error
    }
  })
})(/*{conf}*/)
