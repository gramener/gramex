// Refer https://github.com/vega/vega-parser/blob/master/schema/encode.js
/* exported type_mapper */
/* globals Proxy */

var type_mapper_handler = {
  get: function (obj, prop) {
    return prop in obj ? obj[prop] : 'Number'
  }
}

// Note: convert 'String' to 'Text'
var type_mapper = {
  // symbol
  size: 'Number',
  shape: 'Text',
  // text
  angle: 'Number',
  dx: 'Number',
  dy: 'Number',
  fontSize: 'Number',
  fontWeight: 'Number',
  limit: 'Number',
  radius: 'Number',
  theta: 'Number',
  align: 'Text',
  baseline: 'Text',
  dir: 'Text',
  ellipsis: 'Text',
  font: 'Text',
  fontStyle: 'Text',
  text: 'Text',
  // arc
  startAngle: 'Number',
  endAngle: 'Number',
  padAngle: 'Number',
  innerRadius: 'Number',
  outerRadius: 'Number',
  // cornerRadius: 'Number',
  // line
  interpolate: 'Text',
  tension: 'Number',
  defined: 'Boolean',
  // Rect
  cornerRadius: 'Number',
  // common properties
  x: 'Number',
  x2: 'Number',
  xc: 'Number',
  width: 'Number',
  y: 'Number',
  y2: 'Number',
  yc: 'Number',
  height: 'Number',
  opacity: 'Number',
  fill: 'Color',
  fillOpacity: 'Number',
  stroke: 'Color',
  strokeOpacity: 'Number',
  strokeWidth: 'Number',
  strokeCap: 'Text',
  strokeDash: 'Number',
  strokeDashOffset: 'Number',
  strokeJoin: 'Text',
  strokeMiterLimit: 'Number',
  cursor: 'Text',
  href: 'URL',
  tooltip: 'Any',
  zindex: 'Number'
}

type_mapper = new Proxy(type_mapper, type_mapper_handler)
