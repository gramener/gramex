function draw_charts(e) {
  spec.data.url = "data?" + e.hash.search + "&_by=Segment"
  render_charts('#chart1', 'Sales|sum')
  render_charts('#chart2', 'Quantity|sum')
}
