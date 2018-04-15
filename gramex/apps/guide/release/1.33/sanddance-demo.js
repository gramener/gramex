
/* globals d3, g1 */

// Set up data
for (var i = 0, data = []; i < 111; i++) {
  data.push({
    age: Math.random() * 100,
    weight: Math.random() * 100
  })
}
var width = 500,
    height = 500

// Initialize circles
var selection = d3.select('#sanddance-demo')
  .attr('width', width)
  .attr('height', height)
  .selectAll('circle')
  .data(data)
  .enter()
  .append('circle')
  .attr('cx', 10)
  .attr('cy', 10)
  .attr('stroke', 'white')
  .attr('r', 10)
  .attr('fill', '#444')

// Draw sanddance
var chain = g1.sanddance.chain(
  g1.sanddance({}, {
    x: function () { return Math.random() * (width - 20) },
    y: function () { return Math.random() * (height - 20) },
    delay: 1000,
    duration: 1000
  }),
  g1.sanddance({
    fill: function (d) { return d.age < 50 ? '#5b9bd5' : '#ed7d31' }
  }, {
    delay: 1000,
    duration: 1000
  }),
  g1.sanddance({}, {
    layout: 'grid',
    data: data,
    width: width,
    height: height,
    delay: 1000,
    duration: 1000
  }),
  g1.sanddance({}, {
    layout: 'grid',
    data: data,
    width: width,
    height: height,
    sort: 'age',
    delay: 1000,
    duration: 1000
  }),
  g1.sanddance({}, {
    layout: 'grid',
    data: data,
    width: width,
    height: height,
    sort: 'weight',
    delay: 1000,
    duration: 1000
  }),
  g1.sanddance({}, {
    layout: 'hexpack',
    data: data,
    width: width,
    height: height,
    delay: 1000,
    duration: 1000
  }),
  g1.sanddance({}, {
    layout: 'hexpack',
    data: data,
    width: width,
    height: height,
    sort: 'age',
    delay: 1000,
    duration: 1000
  }),
  g1.sanddance({
    fill: function (d) { return d.weight < 50 ? '#ffc000' : '#4472c4' }
  }, {
    layout: 'hexpack',
    data: data,
    width: width,
    height: height,
    sort: 'weight',
    delay: 1000,
    duration: 1000
  }).on('end', function() {
    selection.call(chain)
  })
)

selection.call(chain)
