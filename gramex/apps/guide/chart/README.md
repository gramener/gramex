title: Gramex Charts

Gramex charts are created using [Vega](http://vega.github.io/vega/). To learn Vega, read the [Vega tutorial](http://gramener.github.io/vegatutorial/).

<div id="pie-chart"></div>

The data for this chart is in [pie-chart.csv](pie-chart.csv):

<pre class="code" data-href="pie-chart.csv"></pre>

The code to create this chart is in [pie-chart.js](pie-chart.js):

<pre class="code" data-href="pie-chart.js"></pre>

<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.16/d3.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vega/2.5.2/vega.min.js"></script>
<script src="pie-chart.js"></script>
<script>
d3.selectAll('.code')
  .each(function() {
    var el = d3.select(this)
    d3.text(el.attr('data-href'), function(error, text) {
      el.text(text)
    })
  })
</script>
