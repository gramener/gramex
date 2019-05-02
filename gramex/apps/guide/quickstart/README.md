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

<i class="fas fa-eye"> After completing step 5, our application should look like [this](index5.html).</i>

### Requirements

In order to complete this tutorial, we will need to:

* [Install and set up Gramex](../install)
* [Download the data](serve/store-sales.csv) and save it at a convenient location on our computer.

*Calls to action, or the steps where something needs to be copy pasted or edited will always be a bullet point similar to these*

## Step 0: Create the Project
<details>
  <summary> Expand This Section </summary>

We need a place to hold together all the files related to our application - including data, source code and configuration files.

* Create a folder at a convenient location on our computer and move the downloaded dataset file into it.

For the remainder of the tutorial, we will refer to this folder as the "project folder". At this time, the project folder should only contain the file `store-sales.csv`.

* To set up the project, create a file named `gramex.yaml` in the project folder, leave it blank for now. 
* Create a second file called `index.html` and put any html you like in there. For now, just a simple bit of text will do, so type in `Hello Gramex!` and save it. 

*index.html and gramex.yaml are the only two files we'll be editing throughout this guide*

```bash
$ echo "Hello Gramex!" > index.html
```

* Having saved the `index.html` file, open up a terminal; navigate to the project folder and type `gramex` to start the server. 

```bash
$ gramex
```

We should start seeing some output now, which is the Gramex server logging its startup sequence. Once we see the following lines, Gramex has fully started, and is ready to accept requests.

```console
INFO    22-Apr 13:34:26 __init__ PORT Listening on port 9988
INFO    22-Apr 13:34:26 __init__ 9988 <Ctrl-B> opens the browser. <Ctrl-D> starts the debugger.
```

At this time, if you open a browser window at [`http://localhost:9988`](http://localhost:9988), you should see the text you had typed in the index.html file. 

<i class="fas fa-eye"> It should look something like [this](index2.html).</i>

Gramex internally watches files for changes, so you can change anything in index.html, and refresh the link in our browser without restarting the server.
</details>

## Step 1: Expose the data through a REST API
<details>
  <summary> Expand This Section </summary>

In order to provide our dashboard with access to the data, we need to create a URL that sends data to the dashboard. To do this, we use a Gramex component called [`FormHandler`](../formhandler).

* Add the formhandler endpoint to our server by adding the following lines to the empty `gramex.yaml` file we had created in Step 0

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

<i class="fas fa-eye"> [Current Output](data?_limit=10).</i>

You could also, visit [http://localhost:9988/data?_limit=10&_format=html](http://localhost:9988/data?_limit=10&_format=html) to see the first ten rows as a simple HTML table.

<i class="fas fa-eye"> [Current Output](data?_limit=10&_format=html).</i>
</details>

## Step 2: Laying out some scaffolding
<details>
  <summary> Expand This Section </summary>

Since we now have access to the data from a REST API, we are ready to start building the frontend.

At the moment, our `index.html` file just has some text in it, let's add some HTML.

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
This is just a bunch of boilerplate that includes css and js files that we'll be using.

If you notice all of our css and js links are relative to a ui/ directory - but we have no such directory in our project folder.

This is because Gramex bundles a lot of common css and js files (bootstrap, lodash, [g1](https://www.npmjs.com/package/g1)) as part of a feature called [UI Components](../uicomponents). 

To use these in our dashboard, we add the following lines to our gramex.yaml:
```yaml
# gramex.yaml
import:
  ui:
    path: $GRAMEXAPPS/ui/gramex.yaml    # Import the UI components
    YAMLURL: $YAMLURL/ui/               # ... at this URL
```
Our overall gramex.yaml now looks like and will not change for the rest of this tutorial.

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
<i class="fas fa-eye"> [Current Output](index6.html)</i>
</details>

## Step 3: Filling in the Data
<details>
  <summary> Expand This Section </summary>
 
The simplest and sometimes most effective way to represent data can be a table. 
Accordingly, Gramex provides a way of embedding tabular data in any HTML page as an interactive table. 
* To use this feature, we insert the following lines in our `index.html`:

```html
<!-- index.html -->
  <div class="formhandler" data-src="data"></div>
  <script>
    $('.formhandler').formhandler({pageSize: 5})
  </script>
```

So overall, our `index.html` file now looks like:
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

The table is interactive. Try playing around with it. Here's a few things we could try:

* Click the dropdown arrows near the column headers to see sorting options
* Try getting the second, third or the 1365th 'page' of the dataset from the menu at the top of the table
* See 20, 50 or more rows at a time in the table from the dropdown menu to the right of the page list.

<i class="fas fa-eye"> [Current Output](index7.html)</i>
</details>

## Step 4: Adding A Chart
<details>
  <summary> Expand This Section </summary>

Let's add a simple barchart to display data grouped by Segment. 

Formhandler automatically does the grouping for us simply by changing the URL.

Attach `?_by=Segment` to any FormHandler URL, [data?_by=Segment](data?_by=Segment) and notice our output has changed.
Each of our numeric columns now has the sum of all rows having a particular Segment value.

FormHandler lets us do a lot of data querying, filtering and grouping just by editing the URL. See [FormHandler Filters](../formhandler/#formhandler-filters) for  list of all possible values.

To actually draw the chart, we'll use a library called [Vega-lite](https://vega.github.io/vega-lite/). Vega-lite is a really simple to use, configuration driven javascript charting library and supports most simple chart types. It also fits in quite well with the javascript ecosystem.

To do this, we add a few pieces to our `index.html`, firstly, we have the schema for the chart itself:

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

* the spec consists of a bunch of nested fields, `width`, `height`, `data` etc
* the data key, is set to the FormHandler URL, with grouping by Segment

```json
"data": {"url": "data?_by=Segment"}
```

* We've set the x and y axis values to `Sales|sum` and `Segment` respectively, telling Vega-lite to plot those quantities from the data that FormHandler returns. 

We also need to add a div in our `index.html` in which we shall place our chart, and a little bit of Javascript code to render the chart.

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

At this stage, our index.html should look like the following:

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

At this point our browser at [localhost:9988/](http://localhost:9988/) should look like <i class="fas fa-eye"> [Current Output](index4.html).</i>
</details>

## Step 4: Final Touches and Making Things Prettier.
<details>
  <summary> Expand This Section </summary>

We can now flex front-end muscle to make our dashboard look slightly better. 

* We've Added a second chart to plot the aggregate sum of Quantity by Segment,
* Hidden a few columns from our dataset to ensure our table fits on the page without horizontal scrolling.
* Modified the vega-lite spec a little,
    * Changed the colours
    * Changed the font
    * Added a Chart Title

<i class="fas fa-eye"> [Final Output](index5.html) </i>

<i class="fas fa-download">Download the final [gramex.yaml](serve/gramex2.yaml).</i>
</details>

## Next steps

If we've followed along with this quickstart, we now have a basic idea of how to build a simple static dashboard with gramex.
To see more of what gramex is able to do and learn more about particular features or how to add interactivity; look at some of our [demos](gramener.com/demo), the rest of our [tutorials](../tutorials), or our [documentation](../).


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