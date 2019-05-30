---
title: Tutorial: Building Interactive Dashboards with Gramex
prefix: g1dashboards
...

[TOC]

In the [quickstart](../../quickstart) we had a dashboard with a
table and a few charts. Often, that is not enough. We need an interactive
way to filter through data. This tutorials deals with adding such
interactivity with Gramex.

After finishing this tutorial, you will:

* have a better understanding of [FormHandler](../../formhandler/) tables,
* be able to create visual elements that react to changes in the data.


## Requirements

This tutorial assumes that you have gone through the
[quickstart](../quickstart) and have successfully built the Gramex
application and created these files:

* [gramex.yaml](../quickstart/output/gramex.yaml.source)
* [store-sales.csv](../quickstart/store-sales.csv)


## Introduction

The chart we made in the quickstart was static, in that it
displayed a single view for the complete dataset - with no way to filter the
data or change the chart dynamically.

To fix this, we need to:

1. detect events like:
    * clicks on chart or table elements
    * filters applied to the table
    * selection or drag interactions with the chart.
2. ensure that every element in our dashboard reponds to these events.

## Step 0: Quickstart Recap

By the end of the [quickstart](../../quickstart), you should have an
application that looks like [this](../../quickstart/index5.html), and has:

  1. a table showing the data,
  2. a bar chart showing sales (order values) aggregated by customer segment,
  3. a bar chart showing order quantities aggregated by customer segment


## Step 1: Working with [FormHandler](../../formhandler/)

The `FormHandler` component is Gramex's primary data model.
Think of FormHandler as 'SQL over HTTP'. If [data](../../quickstart/data)
is our typical data endpoint, then [data?Segment=Consumer](../../quickstart/data?Segment=Consumer)
returns only those rows which have Consumer in the Segment Column. We'll exploit this feature
heavily to build interactive dashboards. Check out the list of possible operations in the
[formhandler documentation](/formhandler/#formhandler-filters).

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">We have covered importing the g1 library in our <kbd>index.html</kbd> in the quickstart's <a href="../../quickstart/#step-2-laying-out-some-scaffolding">scaffolding</a> step as follows:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code class="language-html">&lt;script src="ui/g1/dist/g1.min.js"&gt;&lt;/script&gt;</code></pre>
   </div>
  </div>
</div>


## Step 2: Detecting Changes in the URL

Any interaction with the table changes the URL hash. By storing the state of
interactions in the URL, we can capture a particular view of the data, just by capturing the URL.
g1 provides a way to listen to URL changes via [urlchange](https://code.gramener.com/cto/g1/blob/master/docs/urlchange.md).

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">To see how <kbd>urlchange</kbd> works, put the following snippet in the
     <kbd>&lt;body&gt;</kbd> of <kbd>index.html</kbd>:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="html1" class="language-html"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/urlchange.html').done((e) => {$('#html1').text(e)})</script>


Here, we are logging URL hash changes in the console whenever they happen.
Generally, any function can be run when the url change event is triggered.

After you save the file and refresh the browser, open up the browser console.
Now, whenever you interact with the g1 table, you should see the URL hash printed in the
console.


## Step 3: Redrawing Charts on URL Changes

Now all we have to do is to change the console logging action to something that
redraws the existing charts with the new data present in the FormHandler table.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Recollect that we had the following specification for our charts:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="chartspec" class="language-javascript"></code></pre>
     <p class="text-white">and the following function to draw the charts:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="drawcharts" class="language-javascript"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/chartspec.js').done((e) => {$('#chartspec').text(e)})</script>
<script>$.get('snippets/render_charts.js').done((e) => {$('#drawcharts').text(e)})</script>

Note that the chart gets its data from the `data.url` attribute enclosed in the spec:

```json
{"data": { "url": "data?_by=Segment" }}
```

Therefore, we need to grab the changed URL hash, and set `spec.data.url` to the changed
URL.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">Let's draw a function that grabs the changed URL, sets the <kbd>data.url</kbd> attribute of
     the spec to the new URL, and redraws the charts.</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="drawurlchange" class="language-javascript"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/chart_urlchange.js').done((e) => {$('#drawurlchange').text(e)})</script>


Finally, we must remember to remove the earlier URL change listener (which simply logged changes
to the console), and add our new function as the listener.

<div class="card shadow text-grey bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p class="text-white">The changed event listener function should look be as follows:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="urlchange_final" class="language-javascript"></code></pre>
   </div>
  </div>
</div>
<script>$.get('snippets/urlchange_final.js').done((e) => {$('#urlchange_final').text(e)})</script>

<a href="index1.html">
<p class="alert alert-info" role="alert"><i class="fa fa-eye fa-lg"></i> Our dashboard should look like this.</p>
</a>

Save your file and reload the page. As you click on any value in the table,
the charts will redraw based on the applied filter. As a special case of this, try filtering the
`Segment` column by some value (by clicking on any value in that column) - you should see that
both the bar charts contain only one bar.

Try comparing the order quantities and the sales in the state of Florida across the three segments
(you can do this by selecting Florida under the `State` column), and you should see that while the
Corporate and the Consumer segments place a nearly equal number of orders in Florida, the Corporate
segment has only about two thirds the total sales of the Consumer segment.

## Exercises


## Troubleshooting

### Charts not rendering automatically


## Next Steps / FAQ
