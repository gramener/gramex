function render_charts(chartid, xfield){
  spec.encoding.x.field = xfield
  var view = new vega.View(vega.parse(vl.compile(spec).spec))
  .renderer('svg')
  .initialize(chartid)
  .hover()
  .run()
}
