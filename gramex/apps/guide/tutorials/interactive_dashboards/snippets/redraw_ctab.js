  var baseDataURL = spec.data.url  // keep the original URL handy
  function redrawChartFromURL(e) {
    if (e.hash.relative) { // if the URL hash contains filters, add them to the spec's URL
      spec.data.url = g1.url.parse(baseDataURL).toString() + e.hash.relative
    } else { spec.data.url = baseDataURL }  // otherwise restore to the original URL
    draw_chart()  // draw the chart
  }
