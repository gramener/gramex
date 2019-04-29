---
title: Tutorial: Building Dashboards with Gramex
prefix: g1dashboards
...

[TOC]

In this tutorial, we will build upon the application we created during the
[quickstart](../quickstart) and add some interativity to it,
making it a dashboard in the true sense of the word.

After finishing this tutorial, you will:

* have a better understanding of [FormHandler](../formhandler/) tables,
* be able to create visual elements that react to changes in the data

## Requirements

This tutorial assumes that you have gone through the [quickstart](../quickstart)
and successfully built the Gramex application described in it.


## Introduction

The quickstart focused on laying out the typical scaffolding required by a Gramex
application. Once this is done, we are free to focus our attention on individual
elements within our application, and how they affect with each other. Typical
data applications need to be reactive to new incoming data and user actions.
This tutorial walks through some of the ways of achieving this 
with Gramex.

If you remember, in the quickstart we had sales data from a fictional
superstore. We had displayed this data in an table and added a bar chart that
showed the sales of different customer segments. This chart was static, i.e. it
displayed a metric for the complete dataset. In practice, this is very
limited. Indeed, if data and visual elements in a dashboard were fixed, we would
not need a dashboard. Data for any business problem is ever-growing and ever-changing.
To be able to fully exploit these variations in the data, we need to make the
elements in our dashboard sensitive to them.

In order to accomplish this, we need only to break our problem statement down
into two broad steps:

1. detecting changes in the data, and
2. making elements in the application respond to these changes.

As long as we are able to correctly fulfil these two conditions, we can be
confident that our dashboard is truly dynamic.

Let's get started.

## Step 0: Quickstart Recap

If you have gone through the [quickstart](../quickstart), you should have an
application that looks like [this](../quickstart/index5.html). Specifically,
the application should have:

  1. A table showing the data
  2. A bar chart showing sales (order values) aggregated by customer segment
  3. A bar chart showing order quantities aggregated by customer segment

## Step 1: Working with [FormHandler](../formhandler/) Tables

The `FormHandler` component is Gramex's primary data model. It can connect to a
variety of data sources like files and databases and read data from them.
It can hen expose this data through a [REST API](../quickstart/#step-1-expose-the-data-through-a-rest-api).
In this example, our data source is a [CSV file](../quickstart/store-sales.csv),
and this is how we had set up FormHandler to serve this dataset:

```yaml
url:
  superstore-data:
    pattern: /$YAMLURL/data
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/store-sales.csv
```

You can see the first ten rows of the dataset [here](../quickstart/data?_limit=10)
serialized as JSON.

The JSON can be rendered as an interactive table like this one:

<div class="formhandler" data-src="../quickstart/data?_c=-Order%20ID&_c=-Sub-Category&_c=-Sales&_c=-Quantity&_c=-Ship%20Mode&_c=-Ship%20Date"></div>
<script>
  $('.formhandler').formhandler({pageSize: 5})
</script>

This table comes from [`g1`](https://code.gramener.com/cto/g1) - a JS
library that adds interactivity to various Gramex components. Notice that we
have already imported the g1 library in our `index.html` in the
[scaffolding](../quickstart/#step-2-laying-out-some-scaffolding)
step as follows:

```html
<script src="ui/g1/dist/g1.min.js"></script>
```

You can interact with the g1 FormHandler table in many ways - like changing the
number of rows you want to see in the table, retrieving different 'pages' of the dataset, etc.
You can also interact with the individual columns of the dataset -
you can sort, filter, and hide them. Additionally, you can click on any value within
the table to filter the corresponding column by that value. When
such a filter is applied, a hint appears at the top right corner of the table.
You can click on it to remove the filter.

Our goal, now, is to automatically detect these interactions, and trigger
certain events when the table changes.


## Step 2: Detecting Changes in the URL

Notice that any interaction with the FormHandler table changes the URL -
specifically the URL hash. Thus, watching for changes in the URL hash is a
reliably proxy for detecting changes in the FormHandler table. Not only is this
a proxy, the URL hash actually reflects the arguments supplied to the
FormHandler endpoint. These are arguments that are used to apply
[filters and aggregations](../formhandler/#formhandler-filters) on the dataset.

g1 also provides a way of [listening to changes in the
URL](https://code.gramener.com/cto/g1/blob/master/docs/urlchange.md).
To try it out, put he following snippet in the `<body>` of `index.html`:

```html
<script>
  $('body').urlfilter({target: 'pushState'})
  $(window).on('#?', function(e) { console.log(e.change) })
    .urlchange()
</script>
```

This snippet is essentially telling the browser to log the URL hash changes in the console
whenever they happen. Generally, we can ask the browser to run any function when the url
change event is triggered. We will see an example of this in the next section.
After you save the file and refresh the browser, open up the browser console.
This can be done by right clicking anywhere on the page, and clicking on 'Inspect Element' in the menu.
This will open up a split pane in the browser window. Within this window, navigate to the tab
labeled "Console".

Now, whenever you interact with the g1 table, you should see some output printed in the console.
What you see is a JSON object containing the changed URL hash.

## Step 3: Redrawing Charts on URL Changes

Now that we have managed to trigger some actions whenever the URL changes, all we have to do is
to change these actions to something that redraws the existing charts with the new data present
in the FormHandler table.

Recollect that we had the specification for our charts:

```javascript
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
```

and the following function to draw the charts,

```javascript
  function render_charts(chartid, xfield){
    spec.encoding.x.field = xfield
    var view = new vega.View(vega.parse(vl.compile(spec).spec))
    .renderer('svg')
    .initialize(chartid)
    .hover()
    .run()
  }
```

Also note that the chart gets its data from the `data.url` attribute enclosed in the spec.
Therefore, we need to grab the changed URL hash, and set `spec.data.url` to the new FormHandler
URL. Let's write a simple function which does this:

```javascript
  function draw_charts(e) {
    spec.data.url = "data?" + e.hash.search + "&_by=Segment"
    render_charts('#chart1', 'Sales|sum')
    render_charts('#chart2', 'Quantity|sum')
  }
```

Finally, we must remember to remove the earlier URL change listener (which simply logged changes
to the console), and add our new function as the listener. Thus, the event listener code now looks
like this:

```javascript
  $(window).on('#?', draw_charts)
    .urlchange()
```

[Here](./index1.html) is a working copy of the new dashboard.

After you save your file and reload the page, as you click on any value in the table,
the charts will redraw based on the applied filter. As a special case of this, try filtering the
`Segment` column by some value (by clicking on any value in that column), and you should see that
both the bar charts only one bar.

Try comparing the order quantities and the sales in the state of Florida across the three segments
(you can do this by selecting Florida under the `State` column), and you should see that while the
Corporate and the Consumer segments place a nearly equal number of orders in Florida, the Corporate
segment has only about two thirds the total sales of the Consumer segment.

## Exercises


## Troubleshooting

### Charts not rendering automatically


## Next Steps / FAQ
