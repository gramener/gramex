  var spec = {
    "width": 360,
    "height": 270,
    "data": {"url": "store-sales-ctab"},
    "$schema": "https://vega.github.io/schema/vega-lite/v3.json",
    "encoding": {
      "y": {"field": "Category", "type": "nominal"},
      "x": {"field": "Region", "type": "nominal"}
    },
    "layer": [
      {
        "mark": "rect",
        "selection": {"brush": {"type": "interval"}},
        "encoding": {
          "color": {"field": "Sales", "type": "quantitative",
            "legend": {"format": "0.1s"}}
        }
      },
      {
        "mark": "text",
        "encoding": {
          "text": {"field": "Sales", "type": "quantitative"},
          "color": {
            "condition": {"test": "datum['Sales'] < 100000", "value": "black"},
            "value": "white"
          }
        }
      }
    ]
  }
