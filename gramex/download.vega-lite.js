(function (conf) {
  var id = conf.id || String(Math.random())
  var loading = conf.loading || '<h3>Loading...</h3><i class="fa fa-spin fa-spinner fa-2x"></i>'
  var renderer = conf.renderer || 'svg'
  var spec = conf.spec || {}
  var width = spec.width || 400
  var height = spec.height || 200
  document.write('<div id="' + id + '" style="text-align:center;width:' + width + 'px;height:' + height + 'px">' + loading + '</div>')
  document.addEventListener('DOMContentLoaded', function () {
    var container = document.getElementById(id)
    try {
      // TODO: have a single download.vega.js for vega-lite and family
      new vega.View(vega.parse(vl.compile(spec).spec))
        .renderer(renderer)
        .initialize(container)
        .hover()
        .run()
    } catch (error) {
      container.innerHTML = error
    }
  })
})(/*{conf}*/)
