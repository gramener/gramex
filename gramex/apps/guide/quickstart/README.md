---
title: Quickstart: Dashboard for SuperStore Sales
prefix: Quickstart
...

[TOC]

In this tutorial, we will create a dashboard that analyzes and displays a fictional supermarket's sales grouped by product segment, region and product category.

## Introduction

SuperStore is a fictional department store for whom we will build a data application with Gramex. This
application will allow users to see the store's sales across segments at a glance. After finishing this tutorial,
you will be able to:

1. Read the source data from a REST API.
2. Preview the data in a minimal spreadsheet.
3. Create a chart showing sales and embed it in your application.
4. Filter the data by values and dynamically redraw the chart.
5. Deploy all of the above as a standalone web application.


Here is what the data looks like:

<div class="formhandler" data-src="../quickstart-solution/data"></div>
<script>
  $('.formhandler').formhandler({pageSize: 5})
</script>

Remember that our goal is to display the sales made by the store in concise manner. Thus, the fields relevant
to sales are:

* Sales - the value in USD of a particular order.
* Region, State and City - the place where the sale was made.
* Category, SubCategory - the type of the product that was sold.
* Segment - the type of customer who bought the product.

After completing step 5, your application should look like [this](../quickstart-solution).


## Requirements

In order to complete this tutorial, you will need:

1. [Install and set up Gramex](../install)
2. The SuperStore dataset: Please [download the data](../quickstart-solution/store-sales.csv) and save it at a convenient location on your computer.


## Step 0: Create the Project

We need a place to hold together all the files related to our application - including source code, data and configuration files. Create a folder at a convenient location on your computer and copy the downloaded dataset into it. For the remainder of the tutorial, we will refer to this folder as the "project folder". At this time, the project folder should only contain the file `store-sales.csv`.

To set up the project, create a file named `gramex.yaml` in the project folder, and add the following to it:

```yaml
import:
  ui:
    path: $GRAMEXAPPS/ui/gramex.yaml
    YAMLURL: $YAMLURL/ui/
```

`gramex.yaml` is where all the backend configuration lives. After saving the file, open up a terminal and navigate to the project folder, and start the Gramex server by typing:

```bash
$ gramex
```

You should start seeing some output now, which is the Gramex server logging its startup sequence. By the time you see the following lines, Gramex has fully started, and is ready to accept requests.

```
INFO    22-Apr 13:34:26 __init__ PORT Listening on port 9988
INFO    22-Apr 13:34:26 __init__ 9988 <Ctrl-B> opens the browser. <Ctrl-D> starts the debugger.
```

At this time, if you open a browser window at [`http://localhost:9988`](http://localhost:9988), you should see a list of files in your project folder (which is only `gramex.yaml` and `store-sales.csv` for now).

Gramex internally watches `gramex.yaml` for changes - so we can keep incrementally adding components to the backend, without having to restart the server.


## Step 1: Expose the data through a REST API

In order to provide our dashboard with access to the data, we need to create a URL that _streams_ data to the dashboard. To do this, we use a Gramex component called [`FormHandler`](../formhandler).

Add the formhandler endpoint to your server by adding the following lines to `gramex.yaml`:

```yaml
url:
  superstore-data:
    pattern: /$YAMLURL/data
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/store-sales.csv
```

After you save the file, Gramex will be able to serve the CSV data through the `/data` resource endpoint. To verify this, visit [`http://localhost:9988/data?_limit=10`](http://localhost:9988/data?_limit=10) in your browser. You should now see a JSON payload representing the first ten rows of the dataset.

Since we now have access to the data from a REST API, we are ready to start building the frontend. Create a file named `index.html` with the following content.

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>SuperStore Sales Dashboard</title>
</head>

<body>
  <script src="ui/jquery/dist/jquery.min.js"></script>
  <script src="ui/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
  <script src="ui/popper.js/dist/umd/popper.min.js"></script>
  <script src="ui/lodash/lodash.min.js"></script>
  <script src="ui/g1/dist/g1.min.js"></script>
</body>

</html>
```

Gramex provides a way of embedding tabular data in an HTML page as an interactive table. To use this feature, insert the following lines in the `<body>` of `index.html`:

```html
  <div class="formhandler" data-src="data"></div>
  <script>
    $('.formhandler').formhandler({pageSize: 5})
  </script>
```

After saving the file, when you open [`http://localhost:9988`](http://localhost:9988), you should see a table similar to the one at the top of this page. The table is interactive. Try playing around with it. Here's a few things you could try:

* Click the dropdown arrows near the column headers to see sorting options
* Try getting the second, third or the 1365th 'page' of the dataset from the menu at the top of the table
* See 20, 50 or more rows at a time in the table from the dropdown menu to the right of the page list.

To proceed with the tutorial, return to [`http://localhost:9988`](http://localhost:9988). Now that we have access to the data and can play with it, let's start using it in visualizations.


## Step 2: Making A Chart

FormHandler can also render tabular data as [`seaborn`](https://seaborn.pydata.org/) charts. To include a FormHandler/seaborn chart in your app, insert the following lines in `gramex.yaml`:


```yaml
formhandler-chart:
  pattern: /$YAMLURL/chart
  handler: FormHandler
  kwargs:
    url: $YAMLPATH/data
    function: data.groupby('Segment').sum().reset_index()
    formats:
      barchart:                       # Define a format called barchart
        format: seaborn               # This uses seaborn as the format
        chart: barplot                # Chart can be any standard seaborn chart
        ext: svg                      # Use a matplot backend (svg, pdf, png)
        width: 400                    # Image width in pixels. Default: 640px
        height: 300                   # Image height in pixels. Default: 480px
        dpi: 48                       # Image resolution (dots per inch). Default: 96
        x: Segment                  # additional parameters are passed to barplot()
        y: Sales
```

After saving the file, visit [`http://localhost:9988/chart?_format=barchart`](http://localhost:9988/chart?_format=barchart) in your browser, and you should be able to see the following chart:

![](./img/chart.png)

You can also embed this chat on the dashboard by adding the following lines to the `<body>` of `index.html`:


```html
  <div id="barchart"></div>
  <script>
    $('#barchart').load('chart?_format=barchart')
  </script>
```

Now, at [`http://localhost:9988`](http://localhost:9988), you should see the chart below the formhandler table.
