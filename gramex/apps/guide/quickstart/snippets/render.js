render_charts('#chart1', 'Sales|sum', 'Sales by Segment')
render_charts('#chart2', 'Quantity|sum', 'Quantity by Segment')
function render_charts(chartid, xfield, title) {
  spec.title.text = title
  spec.encoding.x.field = xfield
  var view = new vega.View(vega.parse(vl.compile(spec).spec))
    .renderer('svg')
    .initialize(chartid)
    .hover()
    .run()
}
