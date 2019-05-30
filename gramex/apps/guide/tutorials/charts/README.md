---
title: Tutorial: Creating Interactive Charts with Gramex
prefix: fddcharts
...

[TOC]

In the [previous tutorial](../dashboards/), we saw how filtering a table can
redraw charts. The charts themselves were not interactive. In this
tutorial, we close the loop by making the charts trigger changes in the
FormHandler table. 

## Introduction

We will use a different visualization this time - a colored table which shows total sales for different regions
and product categories.

<div id="chart">
</div>
<script src="../ui/jquery/dist/jquery.min.js"></script>
<script src="../ui/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
<script src="../ui/lodash/lodash.min.js"></script>
<script src="../ui/g1/dist/g1.min.js"></script>
<script src="../ui/vega/build/vega.min.js"></script>
<script src="../ui/vega-lite/build/vega-lite.min.js"></script>
<script src="../ui/vega-tooltip/build/vega-tooltip.min.js"></script>
<script>
  var spec = {
    "width": 360,
    "height": 270,
    "data": {"url": "../store-sales-ctab"},
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
  var view = new vega.View(vega.parse(vl.compile(spec).spec))
  .renderer('svg')
  .initialize('#chart')
  .hover()
  .run()
</script>

Such a table is called a cross-tabulation or a contingency table - it is a
common operation used to aggregate a metric (in this case, sales) across two dimensions
(region and product category).

<a href="output/index2.html">
<p class="alert alert-info" role="alert"><i class="fa fa-eye fa-lg"></i> After finishing this tutorial, you will have an application like this.</p>
</a>

Do play around with the sample application to get an
better idea of our goal for this tutorial. Specifically, take a look at how:

* Applying filters on the 'Region' and 'Category' changes the chart.
* Clicking on different cells in the chart changes the table.


## Requirements

This tutorial assumes that you have gone through the
[previous tutorial](./1_building_interactive_dashboards.md). Specifically, we
will be building on:

1. [FormHandler tables](../dashboards#step-1-working-with-formhandler),
2. how they introduce [changes in the URL](../dashboards#step-2-detecting-changes-in-the-url), and
3. how we use this to [effect changes in the charts](../dashboards#step-3-redrawing-charts-on-url-changes).


## Step 0: Basic Layout and Scaffolding

To begin with, let's just reproduce some of what we did in the last tutorial, beginning
with laying out a FormHandler table.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Add the FormHandler table to your application by adding the following code in the <kbd>&lt;body&gt;</kbd> of <kbd>index.html</kbd>.</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="html1" class="language-html"></code></pre>
   </div>
  </div>
</div>
<script>$.get('../quickstart/snippets/fh.html').done((e) => {$('#html1').text(e)})</script>
<br>

Now we need to add some space in the page to hold the chart.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Add a placeholder for the chart in your page as follows:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="html1" class="language-html">&lt;div id="chart"&gt;&lt;/div&gt;</code></pre>
   </div>
  </div>
</div>
<br>

We will be rendering the chart through a javascript
function, similar to the `draw_charts` function from the previous tutorial.


## Step 1: Performing the Cross-Tabulation with FormHandler

FormHandler can be used to [transform a dataset](../../formhandler#formhandler-transforms)
in a variety of ways. In this example, we will use FormHandler's
[`modify`](../../formhandler/formhandler-modify) function to perform the cross-tabulation.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Add the following to <kbd>gramex.yaml</kbd> to create a HTTP resource which cross-tabulates the data.</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">gramex.yaml</span></a>
       </li>
     </ul>
     <pre><code id="yaml1" class="language-yaml"></code></pre>
   </div>
  </div>
</div>
<script>$.get('../dashboards/snippets/ctab.yaml').done((e) => {$('#yaml1').text(e)})</script>
<br>

In the snippet above, we are creating a new endpoint to serve the cross-tabulated data. After
saving `gramex.yaml`, visit
[`http://localhost:9988/store-sales-ctab`](http://localhost:9988/store-sales-ctab) in your
browser. You should see a JSON array containing 12 objects, each of which represents a
combination of a region and a product category.

_Note_: The transforms supported by FormHandler work seamlessly with
[pandas](https://pandas.pydata.org). Almost evey transformation can be expressed as a
pandas expression. See [FormHandler documentation](../../formhandler) for details.


## Step 2: Drawing the Chart

Just like we had a specification for the bar charts in the previous examples, we will use
a different specification for the color table chart.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Add the following Vega specification for a heatmap chart to your <kbd>index.html</kbd>.</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="ctab_spec" class="language-javascript"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/ctab_spec.js.source').done((e) => {$('#ctab_spec').text(e)})</script>
<br>

Next, let's write a function to compile this specification into a Vega view and draw the
chart.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Add the following function to <kbd>index.html</kbd> to compile the chart specification into a Vega view and draw the chart.</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="draw_ctab" class="language-javascript"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/draw_ctab.js').done((e) => {$('#draw_ctab').text(e)})</script>
<br>

At this point, you should be able to see the chart. Again, as in the previous tutorial,
the next step is to redraw the chart on URL changes.


## Step 3: Redrawing Charts on URL Changes

In the previous tutorial, we had managed to obtain the hash changes in the URL and use
these as queries on the original dataset. In this case,
remember that we are using two _different_ endpoints for the table and the chart - i.e.
[`/data`](http://localhost:9988/data) for the table and
[`/store-sales-ctab`](http://localhost:9988/store-sales-ctab) for the chart. Thus, to
render the chart successfully on URL changes, we must be able to grab filters from the
table and apply them to the cross-tab endpoints. This, too, involves setting the
`data.url` attribute of the chart specification on each change in the URL.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Add the following function to <kbd>index.html</kbd> to get URL changes and apply them to the chart spec.</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="redraw_ctab" class="language-javascript"></code></pre>
     <p class="text-white">Finally, we hook up this function with the URL changes using the following code:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="redraw_ctab_hook" class="language-javascript"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/redraw_ctab.js').done((e) => {$('#redraw_ctab').text(e)})</script>
<script>$.get('snippets/redraw_ctab_hook.js').done((e) => {$('#redraw_ctab_hook').text(e)})</script>
<br>


At this point, the chart should redraw itself based on the table filters. As an example,
try setting the `Region` column to `South`. The chart should contain only one column now.
Similarly, try filtering by some columns except `Category` or `Region`, and the sales
values in the chart should change.


## Step 4: Filtering the Table on Chart Interactions

Finally, we need to close the loop by making the chart itself interactive, i.e.,
filtering the table automatically as any cell in the chart is clicked. Essentially, this
amounts to:

1. determining the region and the category corresponding to the cell where a click is
   registered,
2. converting this information into a [FormHandler filter](../../formhandler/#formhandler-filters)
   query, and
3. redrawing the table according to this query.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Let's put all of this logic together in a function as follows:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="filterTableOnClick" class="language-javascript"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/filterTableOnClick.js').done((e) => {$('#filterTableOnClick').text(e)})</script>
<br>

We need to run this function on _every click_ that is registered on the chart. Therefore,
we will add this function as an event listener to the chart. Since we're drawing the chart
inside the `draw_chart` function, we need to add the event listener within the function as
well.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Change the <kbd>draw_chart</kbd> function to the following:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="draw_chart_final" class="language-javascript"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/draw_chart_final.js').done((e) => {$('#draw_chart_final').text(e)})</script>
<br>

That's it!

Save the HTML file and refresh the page. You should be able to see a two-way
interaction between the chart and the page. Whenever you click on a cell in the chart, a
pair of filters should show up near the top right corner of the table, and conversely whenever
you apply a filter to the table, it should reflect in the chart.


## Exercises


## Troubleshooting

### Charts not rendering automatically


## Next Steps / FAQ
