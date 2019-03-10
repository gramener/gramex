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
  offset: {
    type: 'range',
    attrs: {
      min: 0,
      max: 80,
      step: 1
    }
  },
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
    values: ['Normal', 'Bold', '100', '200', '400', '500', '700', '900']
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
    values: ['Roboto', 'Lato', 'Serif', 'Open Sans', 'Sans-Serif', 'Monospace']
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
  strokeDashOffset: {
    type: 'range',
    attrs: {
      min: 0,
      max: 80,
      step: 1
    }
  },
  strokeJoin:  {
    type: 'select',
    values: ['miter', 'round', 'bevel']
  },
  strokeMiterLimit: 'Number',
  href: 'URL',
  tooltip: 'Any',
  zindex: 'Number',
  scale:	'Text',
  bandPosition:	'Number',
  domain:	'Boolean',
  domainDash:	'Number',
  domainDashOffset:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 80,
      step: 1
    }
  },
  domainColor:	'Color',
  domainOpacity:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 1,
      step: 0.1
    }
  },
  domainWidth:	'Number',
  encode: '     	Object',
  format:	'Text',
  grid:	'Boolean',
  gridColor:	'Color',
  gridDash:	'Number',
  gridDashOffset:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 80,
      step: 1
    }
  },
  gridOpacity:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 1,
      step: 0.1
    }
  },
  gridScale:	'Text',
  gridWidth:	'Number',
  labels:	'Boolean',
  labelAlign:	'Text',
  labelAngle:	{
    type: 'range',
    attrs: {
      min: -180,
      max: 180,
      step: 5
    }
  },
  labelBaseline:	'Text',
  labelBound:	'Boolean',
  labelColor:	'Color',
  labelFlush:	'Boolean',
  labelFlushOffset:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 80,
      step: 1
    }
  },
  labelFont: {
    type: 'select',
    values: ['Roboto', 'Lato', 'Serif', 'Open Sans', 'Sans-Serif', 'Monospace']
  },
  labelFontSize: {
    type: 'range',
    attrs: {
      min: 8,
      max: 36,
      step: 1
    }
  },
  labelFontStyle:	{
    type: 'select',
    values: ['Normal', 'Bold', 'Italic']
  },
  labelFontWeight: {
    type: 'select',
    values: ['Normal', 'Bold', '100', '200', '400', '500', '700', '900']
  },
  labelLimit:	'Number',
  labelOpacity:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 1,
      step: 0.1
    }
  },
  labelOverlap:	'Boolean',
  labelPadding:	'Number',
  labelSeparation:	'Number',
  minExtent:	'Number',
  maxExtent:	'Number',
  position:	'Number',
  ticks:	'Boolean',
  tickColor:	'Color',
  tickCount:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 30,
      step: 1
    }
  },
  tickDash:	'Number',
  tickDashOffset:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 80,
      step: 1
    }
  },
  tickMinStep:	'Number',
  tickExtra:	'Boolean',
  tickOffset:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 80,
      step: 1
    }
  },
  tickOpacity:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 1,
      step: 0.1
    }
  },
  tickRound:	'Boolean',
  tickSize:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 50,
      step: 1
    }
  },
  tickWidth:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 40,
      step: 1
    }
  },
  title:	'Text',
  titleAnchor:	'Text',
  titleAlign:	'Text',
  titleAngle:	{
    type: 'range',
    attrs: {
      min: -180,
      max: 180,
      step: 5
    }
  },
  titleBaseline:	'Text',
  titleColor:	'Color',
  titleFont:	'Text',
  titleFontSize: {
    type: 'range',
    attrs: {
      min: 8,
      max: 36,
      step: 1
    }
  },
  titleFontStyle:	{
    type: 'select',
    values: ['Normal', 'Bold', 'Italic']
  },
  titleFontWeight:  {
    type: 'select',
    values: ['Normal', 'Bold', '100', '200', '400', '500', '700', '900']
  },
  titleLimit:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 100,
      step: 1
    }
  },
  titleOpacity:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 1,
      step: 0.1
    }
  },
  titlePadding:	{
    type: 'range',
    attrs: {
      min: 0,
      max: 80,
      step: 1
    }
  },
  titleX:	'Number',
  titleY:	'Number'
}

type_mapper = new Proxy(type_mapper, type_mapper_handler)
