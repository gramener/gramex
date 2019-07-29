---
title: Tutorial: Building Interactive Dashboards with Gramex
prefix: g1dashboards
...

[TOC]

In the [quickstart](../quickstart) we had a dashboard with a
table and a few charts. Often, that is not enough. We need an interactive
way to filter through data. This tutorials deals with adding such
interactivity with Gramex.


## Introduction

The chart in the quickstart displayed a single view for the complete dataset - with no way to filter the
data or change the chart dynamically.


### Outcome

By the end of this tutorial, you will have learnt to:

1. detect events like:
    * clicks on chart or table elements
    * filters applied to the table
    * selection or drag interactions with the chart.
2. ensure that every element in our dashboard reponds to these events.

The application you have at the end of the quickstart should look like
[this](../quickstart/index5.html).


### Requirements

This tutorial assumes that you have gone through the
[quickstart](../quickstart) and have successfully built the Gramex
application and created these files:

* [gramex.yaml](../quickstart/output/gramex.yaml.source)
* [store-sales.csv](../store-sales.csv)
* [index.html](../quickstart/index5.html.source)


## Step 1: Working with [FormHandler](../../formhandler/)

The `FormHandler` component is Gramex's primary data model.
Think of FormHandler as 'SQL over HTTP'. If [data](../../quickstart/data)
is our typical data endpoint, then [data?Segment=Consumer](../../quickstart/data?Segment=Consumer)
returns only those rows which have "Consumer" in the "Segment" column.
Check out the list of possible operations in the
[formhandler documentation](/formhandler/#formhandler-filters).

Add the formhandler table to the page as follows:

<!-- render:html -->
```html
<link rel="stylesheet" href="../ui/bootstraptheme.css">
<div class="formhandler" data-src="../data?_c=-Ship Date&_c=-Order Date&_c=-Order ID&_c=-Ship Mode&_c=-Quantity&_c=-Discount"></div>
<script src="../ui/jquery/dist/jquery.min.js"></script>
<script src="../ui/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
<script src="../ui/lodash/lodash.min.js"></script>
<script src="../ui/g1/dist/g1.min.js"></script>
<script>
  $('.formhandler').formhandler({pageSize: 5})
</script>
```
[View Source](../dashboards/output/1/index.html){: class="source"}


## Step 2: Detecting Changes in the URL

Any interaction with the table changes the URL hash. By storing the state of
interactions in the URL, we can capture a particular view of the data, just by capturing the URL.
g1 provides a way to listen to URL changes via [urlchange](https://code.gramener.com/cto/g1/blob/master/docs/urlchange.md).

```html
<script>
  $(window).on('#?', function(e) { console.log(e.change) })
    .urlchange()
</script>
```
[View Source](../dashboards/output/2/index.html){: class="source"}


Here, we are logging URL hash changes in the console whenever they happen.
Generally, any function can be run when the url change event is triggered.

After you save the file and refresh the browser, open up the browser console.
Now, whenever you interact with the g1 table, you should see the URL hash printed in the
console.


## Step 3: Redrawing Charts on URL Changes

Now all we have to do is to change the console logging action to something that
redraws the existing charts with the new data present in the FormHandler table.
Recollect that we had the following specification for our charts,
followed by a function to render them.

```html
<script>
var spec = {
  "$schema": "https://vega.github.io/schema/vega-lite/v3.json",
  "description": "A bar chart that sorts the y-values by the x-values.",
  "width": 360,
  "height": 200,
  "data": { "url": "data?_by=Segment" },
  "mark": "bar",
  "encoding": {
    "y": {
      "field": "Segment",
      "type": "nominal",
      "sort": { "encoding": "x" },
      "axis": { "title": "Segment" }
    },
    "x": {
      "field": "Sales|sum",
      "type": "quantitative",
    }
  }
}
function render_charts(chartid, xfield){
  spec.encoding.x.field = xfield
  var view = new vega.View(vega.parse(vl.compile(spec).spec))
  .renderer('svg')
  .initialize(chartid)
  .hover()
  .run()
}
</script>
```

Note that the chart gets its data from the `data.url` attribute enclosed in the spec:

```json
{"data": { "url": "data?_by=Segment" }}
```

Therefore, we need to grab the changed URL hash, and set `spec.data.url` to the changed
URL.Add the following function which grabs the changed URL, sets the <kbd>data.url</kbd>
attribute of the spect to the new URL, and redraws the charts.

```js
function draw_charts(e) {
  spec.data.url = "data?" + e.hash.search + "&_by=Segment"
  render_charts('#chart1', 'Sales|sum')
  render_charts('#chart2', 'Quantity|sum')
}
```

Finally, we must remember to remove the earlier URL change listener (which simply logged changes
to the console), and add our new function as the listener.

The changed event listener should look like:

```javascript
$(window).on('#?', draw_charts).urlchange()
```

[View Source](../dashboards/output/3/index.html){: class="source"}

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

<script src="../tutorial.js"></script>
