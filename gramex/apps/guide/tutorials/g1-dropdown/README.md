---
title: Tutorial: Dropdown Menus & Search
prefix: g1dropdown
...

[TOC]

In the [previous tutorial](../charts) we learnt how to create an interactive
chart that shows the cross-tabulation of sales across geographical areas and
product categories. This tutorial deals with adding even more granularity to the
visualization with dropdown menus and search functionality.

## Introduction
Here's the preview of the data and the corresponding chart.

<div class="formhandler" data-src="../data?_c=-City&_c=-State&_c=-Quantity&_c=-Discount&_c=-Profit&_c=-Order ID&_c=-Order Date&_c=-Ship Date"></div>
<div id="chart"></div>
<script src="../../ui/jquery/dist/jquery.min.js"></script>
<script src="../../ui/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
<script src="../../ui/lodash/lodash.min.js"></script>
<script src="../../ui/g1/dist/g1.min.js"></script>
<script src="../../ui/vega/build/vega.min.js"></script>
<script src="../../ui/vega-lite/build/vega-lite.min.js"></script>
<script src="../../ui/vega-tooltip/build/vega-tooltip.min.js"></script>
<script>
  $('.formhandler').formhandler({ pageSize: 5 })
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
  function draw_chart() {
    var view = new vega.View(vega.parse(vl.compile(spec).spec))
      .renderer('svg')
      .initialize('#chart')
      .hover()
      .run()
    view.addEventListener('click', filterTableOnClick)
  }
  draw_chart()
  var baseDataURL = spec.data.url
  function redrawChartFromURL(e) {
    if (e.hash.relative) {
      spec.data.url = g1.url.parse(baseDataURL).toString() + e.hash.relative
    } else { spec.data.url = baseDataURL }
    draw_chart()
  }
  $('body').urlfilter({target: 'pushState'})
  $(window).on('#', redrawChartFromURL)
    .urlchange()
  function filterTableOnClick(event, item) {
    var qparts = {};
    Object.entries(item.tooltip || item.datum).forEach(([key, val]) => {
      if (!(key == "Sales")) {
        qparts[key] = val;
      }
    })
    if (_.isEmpty(qparts)) { return }
    var url = g1.url.parse(location.hash.replace('#', ''))
    location.hash = url.update(qparts).toString();
  }
</script>

We are able to see the sales across regions and product categories. Suppose that
we want to add even more detail to our dashboard and visualize the same chart,
but this time, optionally filtered by a specific sub-category too. Note that
there are eleven sub-categories of products in our dataset. This can be verified
by [grouping the data](../../formhandler#formhandler-groupby) by the
`Sub-Category` column.

Suppose we want to see the sales of binders. Note that binders don't appear as a
sub-category in the first few columns of the dataset. Thus, we may not see
binders in the `Sub-Category` column unless we jump to the second page of the
table, or increase the preview limit from the default 5 rows to 10 rows. In
general, the data can be filtered by any value in any column, as long as we can
see that value in the table - but in this case, it is not possible to see all
possible subcategories in the preview. In such cases, we might want to add some
element to the page which allows us to:

* see all unique values within a column as a dropdown
* search for values within columns

In this tutorial we will walk through the search and dropdown functionality
provided by [g1](https://www.npmjs.com/package/g1), the Gramex interaction
library, and how it integrates with URL changes and therefore with FormHandlers
and Vega charts.

## Step 0: Laying out the Scaffolding

This tutorial builds upon the previous one. To get started, simply save the
following files into your project folder:

* [`index.html`](../charts/output/index2.html.source)
* [`gramex.yaml`](../../gramex.yaml)
* [`store-sales.csv`](../store-sales.csv)

<a href="../charts/output/index2.html">
<p class="alert alert-info" role="alert"><i class="fa fa-eye fa-lg"></i> Our dashboard should look like this.</p>
</a>

## Step 1: Making a Dropdown Menu

G1 dropdown requires the
[bootstrap-select](https://developer.snapappointments.com/bootstrap-select/)
library and it's dependencies.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Add the following to the <kbd>&lt;body&gt;</kbd> of our <kbd>index.html</kbd>:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="scaffold" class="language-html"></code></pre>
     <p class="text-white">Now, the <kbd>&lt;body&gt;</kbd> of our <kbd>index.html</kbd> should look somewhat like:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="body" class="language-html"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/body.html').done((e) => {$('#body').text(e)})</script>
<script>$.get('snippets/scaffold.html').done((e) => {$('#scaffold').text(e)})</script>

What we have now is an empty dropdown menu, and we need to populate it with the
unique values found in the `Sub-Category` column. For any FormHandler URL, the
unique values in a column can be found by grouping the dataset by that column.
In this case, we can group by the `Sub-Category` column by appending
`?_by=Sub-Category` to the end of the FormHandler URL. You shoud see
[11 unique sub-categories](../data?_by=Sub-Category).

We need to now feed these values into the dropdown menu.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Add the following script to the HTML in order to insert subcategories innto the dropdown menu.</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="dd-subcategories" class="language-html"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/subcategories.html').done((e) => {$('#dd-subcategories').text(e)})</script>

<a href="output/index1.html">
<p class="alert alert-info" role="alert"><i class="fa fa-eye fa-lg"></i> Our dashboard should look like this.</p></a>

Notice that we now have a dropdown menu which contains the unique subcategories
found in the dataset.


## Step 2: Changing the URL on Selection Events

Note that every time we click on something in the dropdown menu, the page
reloads.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">To avoid reloading the page on selection, change the dropdown function as follows:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="pushstate" class="language-html"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/pushstate.html').done((e) => {$('#pushstate').text(e)})</script>

<a href="output/index2.html">
<p class="alert alert-info" role="alert"><i class="fa fa-eye fa-lg"></i> Our dashboard should look like this.</p></a>

By setting the `"target"` option of the `dropdown` function to `"#"`, we
are ensuring that the selected option is added to the hash of the URL.


## Step 3: Enabling Search

A dropdown menu has limited utility. If the number of menu items is too large, a
dropdown can become impractical.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Enable search by setting the <kbd>liveSearch</kbd> option in the dropdown function as follows:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="livesearch" class="language-html"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/livesearch.html').done((e) => {$('#livesearch').text(e)})</script>

<a href="output/index3.html">
<p class="alert alert-info" role="alert"><i class="fa fa-eye fa-lg"></i> Our dashboard should look like this.</p></a>

Notice that a textbox has appeared at the top of the dropdown menu, allowing
search-as-you-type.


## Step 4: Redrawing the Chart on URL Changes

We have successfully managed to make changes to the URL every time an item is
selected from the dropdown menu. In the previous tutorial, we have covered how
to redraw the color table chart whenever the URL changes. Following the same
strategy, we can add event triggers to g1 dropdowns, which redraw the chart
whenever a selection happens.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Change the dropdown function to the following, in order to trigger the chart on a selection event.</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="redraw" class="language-html"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/redraw.html').done((e) => {$('#redraw').text(e)})</script>

<a href="output/index3.html">
<p class="alert alert-info" role="alert"><i class="fa fa-eye fa-lg"></i> Our dashboard should look like this.</p></a>


## Exercises


## Troubleshooting

### Charts not rendering automatically


## Next Steps / FAQ
