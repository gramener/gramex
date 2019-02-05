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
  // title
  orient: 'Text',
  anchor: {
    type: 'select',
    values: ['start', 'middle', 'end']
  },
  color: 'Color',
  frame: 'Text',
  name: 'Text',
  offset: 'Number',
  // symbol
  size: 'Number',
  shape: {
    type: 'select',
    values: ['circle', 'square', 'cross', 'diamond', 'triangle-up', 'triangle-down', 'triangle-right', 'triangle-left']
  },
  cursor: {
    type: 'select',
    values: ['default', 'pointer', 'crosshair', 'move', 'grab']
  },
  // text
  angle: {
    type: 'range',
    attrs: {
      min: -180,
      max: 180,
      step: 5
    }
  },
  dx: {
    type: 'range',
    attrs: {
      min: -20,
      max: 20,
      step: 5
    }
  },
  dy: 'Number',
  fontSize: {
    type: 'range',
    attrs: {
      min: 8,
      max: 36,
      step: 1
    }
  },
  fontWeight: {
    type: 'select',
    values: ['Normal', 'Bold']
  },
  limit: 'Number',
  radius: 'Number',
  theta: 'Number',
  align: {
    type: 'select',
    values: ['left', 'center', 'right']
  },
  baseline: {
    type: 'select',
    values: ['alphabetic', 'top', 'middle', 'bottom']
  },
  dir: {
    type: 'select',
    values: ['ltr', 'rtl']
  },
  ellipsis: 'Text',
  font: {
    type: 'select',
    values: ['Roboto', 'Helvetica Neue', 'Serif', 'Open Sans', 'Sans-Serif', 'Monospace']
  },
  fontStyle: {
    type: 'select',
    values: ['Normal', 'Bold', 'Italic']
  },
  text: 'Text',
  // arc
  startAngle: 'Number',
  endAngle: 'Number',
  padAngle: 'Number',
  innerRadius: 'Number',
  outerRadius: 'Number',
  // cornerRadius: 'Number',
  // line
  interpolate: {
    type: 'select',
    values: ['basis', 'bundle', 'cardinal', 'catmull-rom', 'linear', 'monotone', 'natural', 'step', 'step-after', 'step-before']
  },
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
  opacity: {
    type: 'range',
    attrs: {
      min: 0,
      max: 1,
      step: 0.1
    }
  },
  fill: 'Color',
  fillOpacity: {
    type: 'range',
    attrs: {
      min: 0,
      max: 1,
      step: 0.1
    }
  },
  stroke: 'Color',
  strokeOpacity: {
    type: 'range',
    attrs: {
      min: 0,
      max: 1,
      step: 0.1
    }
  },
  strokeWidth: 'Number',
  strokeCap: {
    type: 'select',
    values: ['butt', 'round', 'square']
  },
  strokeDash: 'Number',
  strokeDashOffset: 'Number',
  strokeJoin:  {
    type: 'select',
    values: ['miter', 'round', 'bevel']
  },
  strokeMiterLimit: 'Number',
  href: 'URL',
  tooltip: 'Any',
  zindex: 'Number'
}

type_mapper = new Proxy(type_mapper, type_mapper_handler)
