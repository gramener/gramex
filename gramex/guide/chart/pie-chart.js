var pie_chart = {
  width: 200,
  height: 200,
  data: [
    {
      "name": "responses",
      "format": {
        "type": "csv",
        "parse": {"responses": "number"}
      },
      "url": "pie-chart.csv"
    }
  ],
  marks: [
    {
      "type": "arc",
      "from": {
        "data": "responses",
        "transform": [
          {
            "type": "pie",
            "field": "responses"
          }
        ]
      },
      "properties": {
        "enter": {
          "x": {"field": {"group": "width"}, "mult": 0.5},
          "y": {"field": {"group": "height"}, "mult": 0.5},
          "innerRadius": {"field": {"group": "width"}, "mult": 0.15},
          "outerRadius": {"field": {"group": "width"}, "mult": 0.45},
          "startAngle": {"field": "layout_start"},
          "endAngle": {"field": "layout_end"},
          "fill": {"value": "steelblue"},
          "stroke": {"value": "#fff"}
        }
      }
    }
  ]
}

vg.parse.spec(pie_chart, function(error, chart) {
  var view = chart({el:"#pie-chart"})
  view.update()
})
