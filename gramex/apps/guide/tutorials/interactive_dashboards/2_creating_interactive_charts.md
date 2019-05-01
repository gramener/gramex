---
title: Tutorial: Creating Interactive Charts with Gramex
prefix: fddcharts
...

[TOC]

In the [previous tutorial](./1_building_interactive_dashboards.md), we learnt how to use a
FormHandler table to trigger changes in charts. However, this is only one part of the
interactivity we want in our dashboard. Note that the charts we had in the previous
tutorial were not interactive by themselves, in that clicking on them does nothing. In this
tutorial, we close the interactivity loop by making the charts trigger changes in the
FormHandler table. This way, both the table and the charts can be used to control each
other, allowing better exploration of data. 

## Introduction

While we will build upon what we learnt in the last tutorial, we will use a different
visualization this time - a colored table which shows total sales for different regions
and product categories.

<div id="chart">
</div>
<script src="../../quickstart/ui/jquery/dist/jquery.min.js"></script>
<script src="../../quickstart/ui/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
<script src="../../quickstart/ui/lodash/lodash.min.js"></script>
<script src="../../quickstart/ui/g1/dist/g1.min.js"></script>
<script src="../../quickstart/ui/vega/build/vega.min.js"></script>
<script src="../../quickstart/ui/vega-lite/build/vega-lite.min.js"></script>
<script src="../../quickstart/ui/vega-tooltip/build/vega-tooltip.min.js"></script>
<script>
  var spec = {
    "width": 360,
    "height": 270,
    "data": {"url": "../../quickstart/store-sales-ctab"},
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

Each row of this table represents a product category, and each column represents a
geographical region. Each cell denotes the total sales in the corresponding category and
the region. Such a table is called a cross-tabulation or a contingency table - it is a
common operation used to aggregate a metric (in this case, sales) across two dimensions
(region and category).

After finishing this tutorial, you will have an application like [this](./index2.html).
Before we proceed with the tutorial, do play around with the sample application to get an
better idea of our goal for this tutorial. Specifically, take a look at how:

* Applying filters on the 'Region' and 'Category' changes the chart.
* Clicking on different cells in the chart changes the table.


## Requirements

This tutorial assumes that you have gone through the
[previous tutorial](./1_building_interactive_dashboards.md). We will be building heavily
on concepts introduced in it, like:

1. [FormHandler tables](./1_building_interactive_dashboards.md#step-1-working-with-formhandler),
2. how they introduce [changes in the URL](./1_building_interactive_dashboards.md#step-2-detecting-changes-in-the-url), and
3. how we use these changes to [effect changes in the charts](./1_building_interactive_dashboards.md#step-3-redrawing-charts-on-url-changes).


## Step 0: Basic Layout and Scaffolding

To begin with, let's just reproduce some of what we did in the last tutorial, beginning
with laying out a FormHandler table, by adding the following code to the `<body>` of our
HTML:

```html
<div class="formhandler" data-src="data"></div>
<script>
  $('.formhandler').formhandler({pageSize: 5})
</script>
```

Now we need to add some space in the page in which the chart would reside. To do this,
add the following lines to the `<body>`:

```html
<div id="chart"></div>
```

This `<div>` element is empty, because we will be rendering the chart through a javascript
function, similar to the `draw_charts` function from the previous tutorial.


## Step 1: Performing the Cross-Tabulation with FormHandler

FormHandler can be used to [transform a dataset](../../formhandler#formhandler-transforms)
in a variety of ways. In this example, we will use FormHandler's
[`modify`](../../formhandler/formhandler-modify) function to perform the cross-tabulation.
To do this, add the following lines to `gramex.yaml`, under the `url:` section.

```yaml
  store-sales-ctab:
    pattern: /$YAMLURL/store-sales-ctab
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/store-sales.csv
      modify: data.groupby(['Category', 'Region'])['Sales'].sum().reset_index()
```

Just as we had earlier created an endpoint to serve data in it's original format, in the
snippet above, we are creating a new endpoint to serve the cross-tabulated data. After
saving `gramex.yaml`, you can try it by visiting
[`http://localhost:9988/store-sales-ctab`](http://localhost:9988/store-sales-ctab) in your
browser. You should see a JSON array containing 12 objects, each of which represents a
combination of a region and a product category.

_Note_: The transforms supported by FormHandler work seamlessly with
[pandas](https://pandas.pydata.org). Almost evey transformation can be expressed as a
pandas expression. See [FormHandler documentation](../../formhandler) for details.


## Step 2: Drawing the Chart

Just like we had a specification for the bar charts in the previous examples, we will use
the following specification for the color table chart:

```javascript
  var spec = {
    "width": 360,
    "height": 270,
    "data": {"url": "store-sales-ctab"},
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
```

Next, let's write a function to compile this specification into a Vega view and draw the
chart, and call that function:

```javascript
  function draw_chart() {
    var view = new vega.View(vega.parse(vl.compile(spec).spec))
      .renderer('svg')
      .initialize('#chart')
      .hover()
      .run()
  }
  draw_chart()
```

At this point, you should be able to see the chart. Again, as in the previous tutorial,
the next step is to redraw the chart on URL changes.


## Step 3: Redrawing Charts on URL Changes

In the previous tutorial, we had managed to obtain the hash changes in the URL and use
these as queries on the original dataset. The approach in this case is a little different.
Remember that we are using two _different_ endpoints for the table and the chart - i.e.
[`/data`](http://localhost:9988/data) for the table and
[`/store-sales-ctab`](http://localhost:9988/store-sales-ctab) for the chart. Thus, to
render the chart successfully on URL changes, we must be able to grab filters from the
table and apply them to the cross-tab endpoints. This, too, involves setting the
`data.url` attribute of the chart specification on each change inn the URL. The following
function does this:

```javascript
  var baseDataURL = spec.data.url  // keep the original URL handy
  function redrawChartFromURL(e) {
    if (e.hash.relative) { // if the URL hash contains filters, add them to the spec's URL
      spec.data.url = g1.url.parse(baseDataURL).toString() + e.hash.relative
    } else { spec.data.url = baseDataURL }  // otherwise restore to the original URL
    draw_chart()  // draw the chart
  }
```

Finally, we hook up this function with the URL changes using the followind code:

```javascript
  $('body').urlfilter({target: 'pushState'})
  $(window).on('#', redrawChartFromURL)
    .urlchange()
```

At this point, the chart should redraw itself based on the table filters. As an example,
try setting the 'Region' column to 'South'. The chart should contain only one column now.
Similarly, try filtering by some columns except 'Category' or 'Region', and the sales
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

Let's put all of this logic together in a function as follows:

```javascript
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
```

We need to run this function on _every click_ that is registered on the chart. Therefore,
we will add this function as an event listener to the chart. Since we're drawing the chart
inside the `draw_chart` function, we need to add the event listener within the function as
well. Change the `draw_chart` function to this:

```javascript
  function draw_chart() {
    var view = new vega.View(vega.parse(vl.compile(spec).spec))
      .renderer('svg')
      .initialize('#chart')
      .hover()
      .run()
    view.addEventListener('click', filterTableOnClick)
  }
```

That's it!

Save the HTML file and refresh the page. You should be able to see a two-way
interaction between the chart and the page. Whenever you click on a cell in the chart, a
pair of filters should show up near the top right corner of the table, and conversely whenever
you apply a filter to the table, it should reflect in the chart.


## Exercises


## Troubleshooting

### Charts not rendering automatically


## Next Steps / FAQ
