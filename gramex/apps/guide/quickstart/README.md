---
title: Quickstart with Gramex
prefix: Quickstart
...

[TOC]

Gramex is a platform that allows users to create visual storyboards from data. This guide follows a concise, step by step approach to create a simple dashboard that analyses and displays a fictional supermarket's sales;
grouped by product segment, region and product category.

## Introduction

SuperStore is a fictional department store for whom we will build a data application with Gramex.
This application will allow users to see the store's sales across segments at a glance. 
After finishing this tutorial, we will be able to:

1. Convert a Data File into a REST API.
2. Preview the data in an interactive table.
3. Create a chart showing sales and embed it in our application.
4. Deploy all of the above as a standalone web application.

Here is what the data looks like:

<div class="formhandler" data-src="data?_c=-Order%20ID&_c=-Sub-Category&_c=-Sales&_c=-Quantity&_c=-Ship%20Mode&_c=-Ship%20Date"></div>
<script>
  $('.formhandler').formhandler({pageSize: 5})
</script>

Remember that our goal is to display the sales made by the store in concise manner. Thus, the fields relevant
to sales are:

* Sales - the value in USD of a particular order.
* Region, State and City - the place where the sale was made.
* Category, SubCategory - the type of the product that was sold.
* Segment - the type of customer who bought the product.

<p class="alert alert-success" role="alert">
<i class="fas fa-eye"></i> After completing step 5, our application should look like <a href="index5.html">this</a>.
</p>

### Requirements

In order to complete this tutorial, we will need to:

* [Install and set up Gramex](../install)
* [Download the data](serve/store-sales.csv) and save it at a convenient location on our computer.

<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <p class="card-text">
    Any action items, points of interest, or places where you have to edit code will be displayed in a card similar to this one.
  </p>
  </div>
</div>

## Step 0: Create the Project
<details>
  <summary> Expand This Section </summary>

We need a place to hold together all the files related to our application - including data, source code and configuration files.

<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <p class="card-text">
    Create a folder at a convenient location on your computer and move the downloaded dataset file into it.
  </p>
  </div>
</div>

<br>
For the remainder of the tutorial, we will refer to this folder as the "project folder". At this time, the project folder should only contain the file `store-sales.csv`.

<div class="card shadow text-white bg-dark">
  <div class="card-body">
    <h4 class="card-title"><i class="fas fa-code"></i></h4>
    <div class="card-text">
    <ul>
      <li>To set up the project, create a file named <kbd>gramex.yaml</kbd> in the project folder, leave it blank for now.</li>
      <li>Create a second file called <kbd>index.html</kbd> and put any html you like in there. For now, just a simple bit of text will do.</li>
    </ul>
    </div>
  </div>
</div>
<br>

`"index.html"` and `"gramex.yaml"` are the only two files we'll be editing throughout this guide. For now, let's put some text in `"index.html"` as follows:
<br>

<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <p class="card-text">
    Open up a terminal, navigate to the project folder and type the following:
  </p>
  </div>
</div>  
<br>

```bash
$ echo "Hello Gramex!" > index.html
```

<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <p class="card-text">
    Having saved the <kbd>index.html</kbd> file, open up a terminal; navigate to the project folder and type <kbd>gramex</kbd> to start the server. 
  </p>
  </div>
</div>  

<br>
We should start seeing some output now, which is the Gramex server logging its startup sequence. Once we see the following lines, Gramex has fully started, and is ready to accept requests.

```console
INFO    22-Apr 13:34:26 __init__ PORT Listening on port 9988
INFO    22-Apr 13:34:26 __init__ 9988 <Ctrl-B> opens the browser. <Ctrl-D> starts the debugger.
```

Note that these may not be the _last_ lines you see in the startup logs, since some Gramex services may start later. Look for these lines in the last few lines.

At this time, if you open a browser window at [`http://localhost:9988`](http://localhost:9988), you should see the text in `"index.html"`.

<p class="alert alert-success" role="alert">
<i class="fas fa-eye"></i> It should look something like <a href="index2.html">this</a>.
</p>

Gramex internally watches files for changes, so you can change anything in `"index.html"`, and refresh the link in your browser without restarting the server.
</details>

## Step 1: Expose the data through a REST API
<details>
  <summary> Expand This Section </summary>

In order to provide our dashboard with access to the data, we need to create a URL that sends data to the dashboard. To do this, we use a Gramex component called [`FormHandler`](../formhandler).

<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <p class="card-text">
    Create a formhandler endpoint on our server by adding the following lines to the empty <kbd>gramex.yaml</kbd> file, which we had created in Step 0:
  </p>
  </div>
</div>

<br>
```yaml
# Gramex.yaml
url:
  superstore-data:
    pattern: /$YAMLURL/data
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/store-sales.csv
```

After you save the file, Gramex will be able to serve the CSV data through the `/data` resource endpoint. To verify this, visit [`http://localhost:9988/data?_limit=10`](http://localhost:9988/data?_limit=10) in our browser. You should now see a JSON payload representing the first ten rows of the dataset.

<p class="alert alert-success" role="alert">
<i class="fa fa-eye"></i> It should look like <a href="data?_limit=10">this</a>.
</p>

You could also, visit [http://localhost:9988/data?_limit=10&_format=html](http://localhost:9988/data?_limit=10&_format=html) to see the first ten rows as a simple HTML table.

<p class="alert alert-success" role="alert">
<i class="fa fa-eye"></i> It should look like <a href="data?_limit=10&_format=html">this</a>.
</p>
</details>

## Step 2: Laying out some scaffolding
<details>
  <summary> Expand This Section </summary>

Since we now have access to the data from a REST API, we are ready to start building the frontend.

<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <p class="card-text">
    At the moment, our <kbd>index.html</kbd> file just has some text in it. Let's add the following HTML to it.
  </p>
  </div>
</div>
<br>
```html
<!-- index.html -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>SuperStore Sales Dashboard</title>
  <link rel="stylesheet" href="ui/bootstraptheme.css">
</head>
<body>
  <div class="placeholder">This div shall hold our data</div>
</body>
  <script src="ui/jquery/dist/jquery.min.js"></script>
  <script src="ui/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
  <script src="ui/lodash/lodash.min.js"></script>
  <script src="ui/g1/dist/g1.min.js"></script>
  <script src="ui/vega/build/vega.min.js"></script>
  <script src="ui/vega-lite/build/vega-lite.min.js"></script>
</html>
```

This is just some boilerplate that includes css and js files we will need.

Note that all of our css and js links are relative to a `ui/` directory - but we have no such directory in our project folder.

This is because Gramex bundles a lot of common css and js files ([bootstrap](https://getbootstrap.com), [lodash](https://lodash.com), [g1](https://www.npmjs.com/package/g1)) as part of a feature called [UI Components](../uicomponents). 

<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <p class="card-text">
    To use these in our dashboard, we add the following lines to our <kbd>gramex.yaml</kbd>:
  </p>
  </div>
</div>
<br>
```yaml
# gramex.yaml
import:
  ui:
    path: $GRAMEXAPPS/ui/gramex.yaml    # Import the UI components
    YAMLURL: $YAMLURL/ui/               # ... at this URL
```

At this point, `gramex.yaml` now contains the following lines and will not change for the rest of this tutorial. Essentially, we are done with the backend configuration.

```yaml
# gramex.yaml
import:
  ui:
    path: $GRAMEXAPPS/ui/gramex.yaml    # Import the UI components
    YAMLURL: $YAMLURL/ui/               # ... at this URL

url:
  superstore-data:
    pattern: /$YAMLURL/data
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/store-sales.csv
```

<p class="alert alert-success" role="alert">
<i class="fa fa-eye"></i> At this time our HTML should look like <a href="index6.html">this</a>.
</p>
</details>

## Step 3: Filling in the Data
<details>
  <summary> Expand This Section </summary>
 
The simplest and sometimes most effective way to represent data can be a table. 
Accordingly, Gramex provides a way of embedding tabular data in any HTML page as an interactive table. 

<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <p class="card-text">
    To show the data as a table, insert the following lines in <kbd>index.html</kbd>:
  </p>
  </div>
</div>
<br>

```html
<!-- index.html -->
  <div class="formhandler" data-src="data"></div>
  <script>
    $('.formhandler').formhandler({pageSize: 5})
  </script>
```

The full `index.html` file now looks like:
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>SuperStore Sales Dashboard</title>
  <link rel="stylesheet" href="ui/bootstraptheme.css">
</head>
<body>
  <div class="formhandler" data-src="data"></div>
</body>
  <script src="ui/jquery/dist/jquery.min.js"></script>
  <script src="ui/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
  <script src="ui/lodash/lodash.min.js"></script>
  <script src="ui/g1/dist/g1.min.js"></script>
  <script>
    $('.formhandler').formhandler({pageSize: 5})
  </script>
</html>
```

After saving the file, when we open [`http://localhost:9988`](http://localhost:9988), we should see a table similar to the one at the top of this page. 

The table is interactive. Try playing around with it. Here's a few things you could try:

<div class="card-deck">
  <div class="card shadow text-white bg-dark">
    <img class="card-img-top" src="img/fh-g1-1.png" alt="Card image cap">
    <div class="card-body">
      <h5 class="card-title">Column Operations</h5>
      <p class="card-text">Click the dropdown arrows near the column headers to see column options.
    </div>
  </div>
  <div class="card shadow text-white bg-dark">
    <img class="card-img-top" src="img/fh-g1-2.png" alt="Card image cap">
    <div class="card-body">
      <h5 class="card-title">Pagination</h5>
      <p class="card-text">Try getting the second, third or the 1365th 'page' of the dataset from the menu at the top of the table.
    </div>
  </div>
  <div class="card shadow text-white bg-dark">
    <img class="card-img-top" src="img/fh-g1-3.png" alt="Card image cap">
    <div class="card-body">
      <h5 class="card-title">Data Size</h5>
      <p class="card-text">See 20, 50 or more rows at a time in the table from the dropdown menu to the right of the page list.
    </div>
  </div>
</div>

<br>
<p class="alert alert-success" role="alert">
<i class="fa fa-eye"></i> At this time our HTML should look like <a href="index7.html">this</a>.
</p>

</details>

## Step 4: Adding A Chart
<details>
  <summary> Expand This Section </summary>

Let's add a simple barchart to display data grouped by Segment. Formhandler automatically does the grouping for us simply by changing the URL. Adding a `?_by` query to any FormHandler URL, like [data?_by=Segment](data?_by=Segment), changes the output: each of our numeric columns now has the sum of all rows having a particular Segment value.

FormHandler lets us do a lot of data querying, filtering and grouping just by editing the URL. See [FormHandler Filters](../formhandler/#formhandler-filters) for  list of all possible values.

To actually draw the chart, we'll use a library called [Vega-lite](https://vega.github.io/vega-lite/). Vega-lite is a really simple to use, configuration driven javascript charting library and supports many common chart types. To draw a chart, we add a few pieces to our `index.html`.

<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <div class="card-text">
    Add the following <span class="font-italic">chart specification</span> to your HTML.
  </div>
  </div>
</div>

<br>

```html
<!-- index.html -->
<script>
var spec = {
  "$schema": "https://vega.github.io/schema/vega-lite/v3.json",
  "description": "A bar chart that sorts the y-values by the x-values.",
  "width": 360,
  "height": 200,
  "data": {"url": "data?_by=Segment"},
  "mark": "bar",
  "encoding": {
    "y": {
      "field": "Segment",
      "type": "nominal",
      "sort": {"encoding": "x"},
      "axis": {"title": "Segment"}
    },
    "x": {
      "field": "Sales|sum",
      "type": "quantitative",
      "axis": {"title": "Sales"}
    }
  }
}
</script>
```

Details of the specification can be found in the vega-lite [docs](https://vega.github.io/vega-lite/docs/), but some things to note:

* the spec consists of a bunch of nested fields, `width`, `height`, `data`, etc
* the data key is set to the FormHandler URL with grouping by Segment: `{"url": "data?_by=Segment"}`
* We've set the x and y axis values to `Sales|sum` and `Segment` respectively, telling Vega-lite to plot those quantities from the data that FormHandler returns. 


<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <div class="card-text">
    Add a div in the page in which to place the chart, and a little bit of Javascript code to render the chart:
  </div>
  </div>
</div>
<br>

```html
<!-- index.html -->
<div id="chart"></div>
<script>
  var view = new vega.View(vega.parse(vl.compile(spec).spec))
      .renderer('svg')
      .initialize('#chart')
      .hover()
      .run()
</script>
```

At this stage, the contents of `index.html` should be as follows:

```html
<!-- index.html -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>SuperStore Sales Dashboard</title>
  <link rel="stylesheet" href="ui/bootstraptheme.css">
</head>
<body>
  <div id="chart"></div>
  <div class="formhandler" data-src="data"></div>
</body>
<script src="ui/jquery/dist/jquery.min.js"></script>
<script src="ui/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
<script src="ui/lodash/lodash.min.js"></script>
<script src="ui/g1/dist/g1.min.js"></script>
<script src="ui/vega/build/vega.min.js"></script>
<script src="ui/vega-lite/build/vega-lite.min.js"></script>
<script>
  $('.formhandler').formhandler({pageSize: 5})
  var spec = {
    "$schema": "https://vega.github.io/schema/vega-lite/v3.json",
    "width": 360,
    "height": 200,
    "description": "A bar chart that sorts the y-values by the x-values.",
    "data": {"url": "data?_by=Segment"},
    "mark": "bar",
    "encoding": {
      "y": {
        "field": "Segment",
        "type": "nominal",
        "sort": {"encoding": "x"},
        "axis": {"title": "Segment"}
      },
      "x": {
        "field": "Sales|sum",
        "type": "quantitative",
        "axis": {"title": "Sales"}
      }
    }
  }
  var view = new vega.View(vega.parse(vl.compile(spec).spec))
      .renderer('svg')
      .height(spec.height)
      .width(spec.width)
      .initialize('#chart')
      .hover()
      .run()
</script>
</html>
```

<p class="alert alert-success" role="alert">
<i class="fa fa-eye"></i> At this time our HTML should look like <a href="index4.html">this</a>.
</p>

</details>

## Step 5: Appearance and Final Touches
<details>
  <summary> Expand This Section </summary>

We can now flex front-end muscle to make our dashboard look slightly better. We will keep this section short, but frontend appearances can be endlessly configured. Feel free to go through the rest of our guides to get a better handle on some of these. 

Let's add a second chart to plot the aggregate sum of Quantity by Segment. It's the same chart - we are just changing the axes. Thus, we can reuse the earlier specification, but we still need to change values of certain fields. So we created a function to which we can pass the fields that need to be updated: the div to draw the chart, the x-axis column name and the title of the chart.

<div class="card shadow text-white bg-dark">
  <div class="card-body">
  <h4 class="card-title"><i class="fas fa-code"></i></h4>
  <div class="card-text">
    Create a function which accepts the fields to be updated, the <code>&lt;div&gt;</code> to place the chart, the X-axis label and the title of the chart.
  </div>
  </div>
</div>
<br>

```javascript
render_charts('#chart1', 'Sales|sum', 'Sales by Segment')
render_charts('#chart2', 'Quantity|sum', 'Quantity by Segment')
function render_charts(chartid, xfield, title) {
  spec.title.text = title
  spec.encoding.x.field = xfield
  var view = new vega.View(vega.parse(vl.compile(spec).spec))
    .renderer('svg')
    .initialize(chartid)
    .hover()
    .run()
}
```

Here are a few more ways in which we can tweak our dashboard:

1. To hide some of the columns from our dataset, we can use a FormHandler filter similar to what we had introduced in Step 4.
2. We can use a feature of UI components, which allows us to override [bootstrap variables by passing url query parameters to the css import line](../uicomponents). For example, setting link-color to black.
3. We can modify the vega-lite configuration of the chart to add a color scale, and change the fonts of the chart. 

<p class="alert alert-success" role="alert">
<i class="fa fa-eye"></i> To see all of this configuration in action, see <a href="index5.html">this</a>.
</p>
<p class="alert alert-success" role="alert">
<i class="fa fa-download"></i> Download the final <a href="serve/gramex2.yaml">gramex.yaml</a>.
</p>

</details>

## Next steps

If you have followed along with this quickstart, you now have a basic idea of how to build a simple static dashboard with Gramex.
To see more of what Gramex's functionality and features; look at:

* our [demos](gramener.com/demo),
* the rest of our [tutorials](../tutorials), and
* our detailed [documentation](../).


## Troubleshooting

- Gramex doesn't start:
    - [Inotify watch limit reached](https://unix.stackexchange.com/questions/s just13751/kernel-inotify-watch-limit-reached)
    - Port is busy
        - Gramex runs on port 9988 by default, you can run `gramex --listen.port=<port number>` to run on an arbritary port. 
- Don't see any text at localhost:9988, instead just a list of files in the directory
    - You may not have a gramex.yaml in your project directory. Create one and restart Gramex.
- CSS/JS Not available.
    - You may have forgotten to add UI Components in Step 2, or could be missing NodeJS; ensure NodeJS is installed, run `gramex setup ui` and restart gramex. If it still doesn't work, open an issue on [github](https://github.com/gramener/gramex) or email cto@gramener.com  
- vega chart not rendering for some reason
    - You may have forgotten to include vega and vega lite dependencies in step 2.
