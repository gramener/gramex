  function draw_chart() {
    var view = new vega.View(vega.parse(vl.compile(spec).spec))
      .renderer('svg')
      .initialize('#chart')
      .hover()
      .run()
    view.addEventListener('click', filterTableOnClick)
  }
