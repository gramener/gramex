---
title: Tutorial: Building Interactive Dashboards with Gramex
prefix: g1dashboards
...

[TOC]

At the end of the [quickstart](../../quickstart) we had a very simple dashboard, with an
interactive table and a few charts. However, that in itself is not very interesting. We would
want some ways to filter through data, either by clicking or selecting certain visual elements in
the charts etc. This guide will walk through the process of creating such interactive,
URL driven dashboards with gramex.

After finishing this tutorial, you will:

* have a better understanding of [FormHandler](../../formhandler/) tables,
* be able to create visual elements that react to changes in the data.

## Requirements

This tutorial assumes that you have gone through the [quickstart](../../quickstart)
and have successfully built the Gramex application described in it. Some knowledge of basic
Javascript and Jquery would also be helpful, but is not required.


## Introduction

Recall that in the quickstart we had sales data from a fictional superstore.
We had displayed this data in an table and added a bar chart that
showed the sales of different customer segments. This chart was static, in that it
displayed a single view for the complete dataset - we had no ability to filter or zoom or look
into a subset of the data - or change the chart in any way at all.

To fix this, there are two things we need to accomplish:

1. detect events like:
    * clicks on chart or table elements
    * filters applied to the table
    * selection or drag interactions with the chart.
2. ensure that every element in our dashboard reponds to these events.

Let's get started.


## Step 0: Quickstart Recap

If you have gone through the [quickstart](../../quickstart), you should have an
application that looks like [this](../../quickstart/index5.html). Specifically,
the application should have:

  1. A table showing the data
  2. A bar chart showing sales (order values) aggregated by customer segment
  3. A bar chart showing order quantities aggregated by customer segment


## Step 1: Working with [FormHandler](../../formhandler/)

The `FormHandler` component is Gramex's primary data model. It can connect to a
variety of data sources like files and databases and read data from them.
It can then expose this data through a [REST API](../../quickstart/#step-1-expose-the-data-through-a-rest-api).
The most powerful feature of FormHandler is that we can filter, aggregate, sort and
otherwise query the data simply by adding URL Query parameters.
Think of FormHandler as 'SQL over HTTP'. This means that if [data](../../quickstart/data)
is our typical data endpoint, then [data?Segment=Consumer](../../quickstart/data?Segment=Consumer)
returns only those rows which have Consumer in the Segment Column. We'll exploit this feature
heavily to build interactive dashboards. Check out the list of possible operations in the
[formhandler documentation](/formhandler/#formhandler-filters)

Data from FormHandler can also be rendered as an interactive table like this one:

<div class="formhandler" data-src="../../quickstart/data?_c=-Order%20ID&_c=-Sub-Category&_c=-Sales&_c=-Quantity&_c=-Ship%20Mode&_c=-Ship%20Date"></div>
<script>
  $('.formhandler').formhandler({pageSize: 5})
</script>

This table comes from [`g1`](https://npmjs.com/package/g1) - a JS
library that adds interactivity to various Gramex components.
We can easily sort, filter or paginate through the data using the table.

<div class="card shadow text-white bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p>We have covered importing the g1 library in our <kbd>ndex.html</kbd> in the quickstart's <a href="../../quickstart/#step-2-laying-out-some-scaffolding">scaffolding</a> step as follows:</p>
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

Notice that any interaction with the table changes the URL - specifically the URL hash.
This is intentional, by storing the state of various interactions and filters in the URL, we
create the ability to share a particular view of the data, just by sharing the URL.
You could do this manually, by attaching an event listener to <kbd>window.location</kbd> attribute and parsing it,
but g1 provides a simpler way to this via [urlchange](https://code.gramener.com/cto/g1/blob/master/docs/urlchange.md).

<div class="card shadow text-white bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p>To see how <kbd>urlchange</kbd> works, put the following snippet in the
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


This snippet is essentially telling the browser to log the URL hash changes in the console
whenever they happen. Generally, we can ask the browser to run any function when the url
change event is triggered.
After you save the file and refresh the browser, open up the browser console.
This can be done by right clicking anywhere on the page, and clicking on 'Inspect Element' in the menu.
This will open up a split pane in the browser window. Within this window, navigate to the tab
labeled "Console".

Now, whenever you interact with the g1 table, you should see some output printed in the console.
What you see is a JSON object containing the changed URL hash.


## Step 3: Redrawing Charts on URL Changes

Now that we have managed to trigger some action whenever the URL changes, all we have to do is
to change this action to something that redraws the existing charts with the new data present
in the FormHandler table.

<div class="card shadow text-white bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p>Recollect that we had the following specification for our charts:</p>
     <ul class="nav nav-tabs">
       <li class="nav-item">
         <a class="nav-link active"><i class="fas fa-code"></i> <span class="text-monospace">index.html</span></a>
       </li>
     </ul>
     <pre><code id="chartspec" class="language-javascript"></code></pre>
     <p>and the following function to draw the charts:</p>
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

<div class="card shadow text-white bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p>Let's draw a function that grabs the changed URL, sets the <kbd>data.url</kbd> attribute of
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

<div class="card shadow text-white bg-dark">
  <div class="card-body">
   <div class="card-text">
     <p>The changed event listener function should look be as follows:</p>
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
