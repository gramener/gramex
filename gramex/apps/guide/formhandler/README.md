---
title: FormHandler connects to data
prefix: FormHandler
...

[TOC]

[FormHandler][formhandler] lets you read & write data from files and databases.

Here is a sample configuration to read data from a CSV file:

```yaml
url:
  flags:
    pattern: /$YAMLURL/flags
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/flags.csv
```

You can read from multiple file formats as well as databases. The URL may be a
[gramex.cache.open](../cache/#data-caching) path. For example:

```yaml
    url: /path/to/file.csv      # Reads the CSV file

    url: /path/to/file.xlsx     # Reads first sheet from file.xlsx

    url: /path/to/file.csv      # Any additional parameters are passed to
    delimiter: '|'              # gramex.cache.open, which uses pd.read_csv

    ext: xlsx                   # Passes ext=xlsx to gramex.cache.open
    url: /path/to/filename      # which treats this file as an Excel file

    url: /path/to/file.xlsx     # Reads the sheet named sales
    sheetname: sales

    url: /path/to/file.hdf      # Reads the dataframe at key named 'sales'
    key: sales

    url: /path/to/file.parquet  # Reads the parquet file

    url: /path/to/file.feather  # Reads the feather file
```

You can read from a HTTP or HTTPS URL.

```yaml
    # This URL is read once and cached forever
    url: https://learn.gramener.com/guide/formhandler/flags.csv
    ext: csv          # Explicitly specify the extension for HTTP(S) urls
```

This is cached permanently unless the URL is changed. You change the URL using
[FormHandler parameters](#formhandler-parameters) like below:

```yaml
    # This URL is refreshed every time the FormHandler gets a new ?v=...
    url: https://learn.gramener.com/guide/formhandler/flags.csv?version={v}
    ext: csv          # Explicitly specify the extension for HTTP(S) urls
```

Additional parameters like `delimiter:`, `ext:`, etc are passed to
[gramex.cache.open](../cache/#data-caching), which uses the Pandas ``read_*``
methods.

`url:` can also be an SQLAlchemy URL. For example:

```yaml
    url: 'mysql+pymysql://$USER:$PASS@server/db'    # Reads from MySQL
    table: sales

    url: 'postgresql://$USER:$PASS@server/db'       # Reads from PostgreSQL
    table: sales

    url: 'oracle://$USER:$PASS@server/db'           # Reads from Oracle
    table: sales

    url: 'mssql+pyodbc://$USER:$PASS@dsn'           # Reads from MS SQL
    table: sales

    url: 'sqlite:///D:/path/to/file.db'             # Reads from SQLite
    table: sales
```

Additional parameters like `table:`, `encoding:`, etc are passed to
[gramex.cache.query](../cache/#query-caching), which uses
``sqlalchemy.create_engine``.

## FormHandler formats

By default, FormHandler renders data as JSON. Use `?_format=` to change that.

- Default: [flags](flags)
- HTML: [flags?_format=html](flags?_format=html)
- CSV: [flags?_format=csv](flags?_format=csv)
- JSON: [flags?_format=json](flags?_format=json)
- XLSX: [flags?_format=xlsx](flags?_format=xlsx)
- Table: [flags?_format=table](flags?_format=table) from **v1.23** - an interactive table viewer

To include the table format, you must include this in your gramex.yaml:

```yaml
import:
  path: $GRAMEXPATH/apps/formhandler/gramex.yaml
  YAMLURL: $YAMLURL         # Mount this app at the current folder
```

You can also create custom PPTX downloads using FormHandler. For example, this
configuration adds a custom PPTX format called `pptx-table`:

```yaml
formhandler-flags:
  pattern: /$YAMLURL/flags
  handler: FormHandler
  kwargs:
    url: $YAMLPATH/flags.csv
    formats:
      pptx-table:                       # Define a format called pptx-table
        format: pptx                    # It generates a PPTX output
        source: $YAMLPATH/input.pptx    # ... based on input.pptx
        change-table:                   # The first rule to apply...
          Table:                        # ... takes all shapes named Table
            table:                      # ... runs a "table" command (to update tables)
              data: data['data']        # ... using flags data (default name is 'data)
```

- Download the output at [flags?_format=pptx-table](flags?_format=pptx-table&_limit=10&_c=ID&_c=Name&_c=Continent&_c=Stripes).
- Download the [input.pptx](input.pptx) used as a template

### Date parsing

If a file has dates stored as text, use the `parse_dates:` setting to convert it
to a datetime.

For example:

```yaml
formhandler-...:
  pattern: /$YAMLURL/...
  handler: FormHandler
  kwargs:
    url: $YAMLPATH/data.csv
    parse_dates: start_date                 # convert start_date from string to datetime
    parse_dates: [start_date, end_date]     # convert both columns from string to datetime
```

By default, datetimes are rendered in JSON as
[`epoch`](https://en.wikipedia.org/wiki/Unix_time) times, i.e. time in
milliseconds from 1-Jan-1980 UTC.  Use `formats.date_format: iso` to change this
to ISO. This returns something like `2019-01-01T00:00:00.000Z`.

```yaml
formhandler-...:
  pattern: /$YAMLURL/...
  handler: FormHandler
  kwargs:
    url: ...
    formats:
      json:
        date_format: iso            # Convert to ISO format instead of epoch
```

The ISO format can capture the time zone and is more human readable. Both ISO
and epoch can be converted into JavaScript date objects via `new Date(date)`.

## FormHandler tables

**v1.28**. Gramex includes the [g1][g1] library that includes a FormHandler
table component. To use it, add the following code:

```html
<link rel="stylesheet" href="ui/bootstraptheme.css"/>     <!-- Add bootstrap -->
<div class="formhandler" data-src="flags"></div>          <!-- Insert component here -->
<!-- Include JS dependencies  -->
<script src="ui/lodash/lodash.min.js"></script>
<script src="ui/jquery/dist/jquery.min.js"></script>
<script src="ui/popper.js/dist/umd/popper.min.js"></script>
<script src="ui/bootstrap/dist/js/bootstrap.min.js"></script>
<script src="ui/g1/dist/g1.min.js"></script>
<script>
  // Render the FormHandler table
  $('.formhandler').formhandler()
</script>
```

This requires the [UI components library](../uicomponents/) mounted at `ui/`.

<div class="example">
  <a class="example-demo" href="table.html">FormHandler table example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/formhandler/table.html">Source</a>
</div>

You can configure the data attributes:

- `data-src`: FormHandler URL endpoint
- `data-columns="col1,col2,col3"`: comma-separated column names to display
- `data-table=""`: hides the table
- `data-count=""`: hides the row count
- `data-page=""`: hides the page control
- `data-page-size="10"`: sets the page size to 10 (default: 100)
- `data-size=""`: hides the page size control
- `data-size-values="10,50,100"`: defines page size values (default: `10,20,50,100,500,1000`)
- `data-export=""`: hides the export control
- `data-filters=""`: hides the applied filters control

More options can be provided to `$().formhandler()` via JavaScript. See the
[API documentation][g1-formhandler] for details.

[g1]: https://code.gramener.com/cto/g1/
[g1-formhandler]: https://code.gramener.com/cto/g1/#formhandler

## FormHandler charts

**v1.28**. FormHandler supports [seaborn](https://seaborn.pydata.org/) charts.
To render FormHandler data as charts, use:

```yaml
formhandler-chart:
  pattern: /$YAMLURL/chart
  handler: FormHandler
  kwargs:
    url: $YAMLPATH/flags.csv
    function: data.groupby('Continent').sum().reset_index()
    formats:
      barchart:                       # Define a format called barchart
        format: seaborn               # This uses seaborn as the format
        chart: barplot                # Chart can be any standard seaborn chart
        ext: png                      # Use a matplot backend (svg, pdf, png)
        width: 400                    # Image width in pixels. Default: 640px
        height: 300                   # Image height in pixels. Default: 480px
        dpi: 48                       # Image resolution (dots per inch). Default: 96
        x: Continent                  # additional parameters are passed to barplot()
        y: c1
        headers:
          Content-Type: image/png     # Render as a PNG image
```

The URL [chart?_format=barchart][barchart] renders the chart image.

[![Bar plot][barchart]][barchart]

To insert an SVG via AJAX, set `ext: svg` and load it via AJAX.

```html
<div id="barchart-svg"></div>
<script>
$('#barchart-svg').load('chart?_format=barchart-svg')
</script>
```

<div id="barchart-svg"></div>
<script>
$('#barchart-svg').load('chart?_format=barchart-svg')
</script>

The format options are formatted using the URL arguments via `{arg}`
example:

```yaml
      x: '{xcol}'   # The X axis for barplot comes from ?xcol=
      y: '{ycol}'   # The Y axis for barplot comes from ?ycol=
```

The URL `?xcol=Continent&ycol=c3` draws c3 vs Continents:

[![c3 by Continent][barplot-Continent-c3]][barplot-Continent-c3]

Image dimensions can be controlled via URL arguments. For example:

```yaml
      width: '{width}'  # The width of barplot comes from ?width=
      height: 200       # The height of barplot is fixed
```

[![c2 by Continent 200px wide][barplot-200]][barplot-200]
[![c2 by Continent 300px wide][barplot-300]][barplot-300]

More chart types can be created. See the [Seaborn API](https://seaborn.pydata.org/api.html) for examples.

### Categorical plots

[![barplot][barplot]][barplot]
[![stripplot][stripplot]][stripplot]
[![swarmplot][swarmplot]][swarmplot]
[![boxplot][boxplot]][boxplot]
[![violinplot][violinplot]][violinplot]
[![lvplot][lvplot]][lvplot]
[![pointplot][pointplot]][pointplot]

### Regression plots

[![regplot][regplot]][regplot]
[![residplot][residplot]][residplot]

### Grid plots

[![jointplot][jointplot]][jointplot]
[![factorplot][factorplot]][factorplot]
[![lmplot][lmplot]][lmplot]

### Matrix plots

[![heatmap][heatmap]][heatmap]
[![clustermap][clustermap]][clustermap]

More examples to be added.

[barchart]: chart?_format=barchart
[barplot-Continent-c3]: chart?_format=barchart-custom&xcol=Continent&ycol=c3
[barplot-200]: chart?_format=barchart-custom-size&xcol=Continent&ycol=c2&width=200
[barplot-300]: chart?_format=barchart-custom-size&xcol=Continent&ycol=c2&width=300
[barplot]: categorical?chart=barplot&xcol=Continent&ycol=c1&width=350&height=200
[stripplot]: categorical?chart=stripplot&xcol=Continent&ycol=c1&width=350&height=200
[swarmplot]: categorical?chart=swarmplot&xcol=Continent&ycol=c1&width=350&height=200
[boxplot]: categorical?chart=boxplot&xcol=Continent&ycol=c1&width=350&height=200
[violinplot]: categorical?chart=violinplot&xcol=Continent&ycol=c1&width=350&height=200
[lvplot]: categorical?chart=lvplot&xcol=Continent&ycol=c1&width=350&height=200
[pointplot]: categorical?chart=pointplot&xcol=Continent&ycol=c1&width=350&height=200
[regplot]: categorical?chart=regplot&xcol=c2&ycol=c1&width=350&height=200
[residplot]: categorical?chart=residplot&xcol=c2&ycol=c1&width=350&height=200
[jointplot]: categorical?chart=jointplot&xcol=c1&ycol=c3&width=350&height=200
[factorplot]: categorical?_format=facet&chart=factorplot&xcol=c2&ycol=c5&hue=Stripes&width=350&height=200
[lmplot]: categorical?_format=facet&chart=lmplot&xcol=c1&ycol=c3&hue=Stripes&width=350&height=200
[heatmap]: numerical?_format=matrix&chart=heatmap&width=350&height=200
[clustermap]: numerical?_format=matrix&chart=clustermap&width=350&height=200

## FormHandler Vega charts

**v1.31**. FormHandler supports [Vega](https://vega.github.io/) charts. To use it, define a [format](#formhandler-formats) using `format: vega`. For example:

```yaml
url:
  formhandler-vega-1:
    pattern: /$YAMLURL/vega-1
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/flags.csv
      formats:
        barchart:           # Allows ?_format=barchart
          format: vega
          spec:
            "$schema": "https://vega.github.io/schema/vega/v4.json"
            ...   # The rest of the Vega spec comes here
```

When you visit [vega-1?_format=barchart](vega-1?_format=barchart) it renders JavaScript that creates the chart. To include it on your page, just add `<script src="vega-1?_format=barchart" data-id="chart1"></script>` where you want to include the chart, like below:

```html
<script src="vega-1?_format=barchart" data-id="chart1"></script>
... rest of the page ...
<script src="ui/vega/build/vega.min.js"></script>
```

This script draws a barchart from [`/vega-1`](http://github.com/gramener/gramex/blob/master/gramex/apps/guide/formhandler/vega.yaml) formhandler data within `<div id="chart1"></div>`. If `data-id` is missing, random ID is created.

To manipulate the `Vega` object, use this:

```js
//  Returns the vega object
var view = document.querySelector('#chart1').vega
```

To redraw the chart with new data (e.g. `vega-1?_format=barchart&Continent!=Africa`)

```js
var url = 'vega-1?_format=json&Continent!=Africa'
$.getJSON(url)
  .done(function(new_data) {
    var view = document.querySelector('#chart1').vega
    // Suppose, Vega spec in above example uses `data` as (name)[https://vega.github.io/vega/docs/data/]

    // Remove old data from namespace `data`
    view.remove('data', function(d) {return true}).run()
    // Insert new values into namespace `data`
    view.insert('data', new_data).run()
  })
```

Note: For Vega-Lite, default dataset namespace is `source_0`

### Parameter Substitution

Vega spec can be formatted using the path arguments and URL query parameters.

```yaml
url:
  formhandler-vega-lite-1:
    pattern: /$YAMLURL/vega-lite-1
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/flags.csv
      function: data.groupby('Continent').sum().reset_index()
      default:
        COL_METRIC: c1                   # COL_METRIC defaults to c1
        COL_DIMENSION: Continent         # COL_DIMENSION defaults to Continent
        CHART_TYPE: bar                  # CHART_TYPE defaults to bar
      formats:
        barchart:
          format: vega-lite
          spec:
            "$schema": "https://vega.github.io/schema/vega-lite/v2.json"
            mark: '{CHART_TYPE}'
            encoding:
              x: {field: '{COL_DIMENSION}', type: ordinal}     # COL_DIMENSION set to dim for ?COL_METRIC=dim
              y: {field: '{COL_METRIC}', type: quantitative}   # COL_METRIC set to val for ?COL_METRIC=val
```

Using the above endpoint, below url draws `bar` chart with `y=c4` and `x=Continent`

```html
<script src="vega-lite-1?_format=barchart&CHART_TYPE=bar&COL_METRIC=c4"></script>
```

<div class="example">
  <a class="example-demo" href="vega-examples">FormHandler Vega Chart examples</a>
  <a class="example-src" href="vega.yaml">Source</a>
</div>

Similarly, [Vega-Lite](https://vega.github.io/vega-lite/) charts are also supported. Use `format: vega-lite` instead of `format: vega`. To include it on your page, just add `<script src="...?_format=barchart"></script>` where you want to include the chart, like below:

```html
<script src="vega-lite-1?_format=barchart"></script>
... rest of the page ...
<script src="ui/vega/build/vega.min.js"></script>
<script src="ui/vega-lite/build/vega-lite.min.js"></script>
```

<div class="example">
  <a class="example-demo" href="vega-lite-examples">FormHandler Vega-Lite Chart examples</a>
  <a class="example-src" href="vega-lite.yaml">Source</a>
</div>

Similarly, Use `format: vegam` for [Vegam](https://www.npmjs.com/package/vegam) charts.

```html
<script src="vegam-1?_format=barchart"></script>
... rest of the page ...
<script src="ui/vega/build/vega.min.js"></script>
<script src="ui/vega-lite/build/vega-lite.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vegam@0.0.2/dist/vegam.min.js"></script>
```

<div class="example">
  <a class="example-demo" href="vegam-examples">FormHandler Vegam Chart examples</a>
  <a class="example-src" href="vegam.yaml">Source</a>
</div>

## FormHandler downloads

CSV and XLSX formats are downloaded as `data.csv` and `data.xlsx` by default.
You can specify `?_download=` to download any format as any filename.

- Default is data.xlsx: [flags?_format=xlsx](flags?_format=xlsx)
- Download as filename.xlsx: [flags?_format=xlsx&_download=filename.xlsx](flags?_format=xlsx&_download=filename.xlsx)
- Download JSON as filename.json: [flags?_download=filename.json](flags?_download=filename.json)
- Download HTML as filename.html: [flags?_format=html&_download=filename.html](flags?_format=html&_download=filename.html)

## FormHandler filters

The URL supports operators for filtering rows. The operators can be combined.

- [?Continent=Europe](flags?Continent=Europe&_format=html) ► Continent = Europe
- [?Continent=Europe&Continent=Asia](flags?Continent=Europe&Continent=Asia&_format=html)
  ► Continent = Europe OR Asia. Multiple values are allowed
- [?Continent!=Europe](flags?Continent!=Europe&_format=html) ► Continent is NOT Europe
- [?Continent!=Europe&Continent!=Asia](flags?Continent!=Europe&Continent!=Asia&_format=html)
  ► Continent is NEITHER Europe NOR Asia
- [?Shapes](flags?Shapes&_format=html) ► Shapes is not NULL
- [?Shapes!](flags?Shapes!&_format=html) ► Shapes is NULL
- [?c1>=10](flags?c1>=10&_format=html) ► c1 > 10 (not >= 10)
- [?c1>~=10](flags?c1>~=10&_format=html) ► c1 >= 10. The `~` acts like an `=`
- [?c1<=10](flags?c1<=10&_format=html) ► c1 < 10 (not <= 10)
- [?c1<~=10](flags?c1<~=10&_format=html) ► c1 <= 10. The `~` acts like an `=`
- [?c1>=10&c1<=20](flags?c1>=10&c1<=20&_format=html) ► c1 > 10 AND c1 < 20
- [?Name~=United](flags?Name~=United&_format=html) ► Name matches &_format=html
- [?Name!~=United](flags?Name!~=United&_format=html) ► Name does NOT match United
- [?Name~=United&Continent=Asia](flags?Name~=United&Continent=Asia&_format=html) ► Name matches United AND Continent is Asia

To control the output, you can use these control arguments:

- Limit rows: [?_limit=10](flags?_limit=10&_format=html) ► show only 10 rows
- Offset rows: [?_offset=10&_limit=10](flags?_offset=10&_limit=10&_format=html) ► show only 10 rows starting, skipping the first 10 rows
- Sort by columns: [?_sort=Continent&_sort=Name](flags?_sort=Continent&_sort=Name&_format=html) ► sort first by Continent (ascending) then Name (ascending)
- Sort order: [?_sort=-Continent&_sort=-ID](flags?_sort=-Continent&_sort=-ID&_format=html) ► sort first by Continent (descending) then ID (descending)
- Specific columns: [?_c=Continent&_c=Name](flags?_c=Continent&_c=Name&_format=html) ► show only the Continent and Names columns
- Exclude columns: [?_c=-Continent&_c=-Name](flags?_c=-Continent&_c=-Name&_format=html) ► show all columns except the Continent and Names columns
- Add metadata: [?_meta=y](flags?_c=-Continent&_offset=10&_limit=10&_format=html&_meta=y) ► return all available metadata as HTTP headers

Note: You can use `FormHandler` to render specific columns in navbar filters using `?_c=`.


## FormHandler groupby

**v1.38**. The URL supports grouping by columns using `?_by=col`. For example:

- [?_by=Continent](flags?_by=Continent&_format=table): group by Continent, and sum all numeric columns.
  ([Test on SQLite](db?_by=Continent&_format=table))
- [?_by=Text](flags?_by=Text&_format=table): group by Text, and sum all numeric columns.
  ([Test on SQLite](db?_by=Text&_format=table))
- [?_by=Text&_by=Symbols](flags?_by=Text&_by=Symbols&_format=table): group by Text *and* by Symbols.
  ([Test on SQLite](db?_by=Text&_by=Symbols&_format=table))

You can specify custom aggregations using `?_c=col|aggregation`. For example:

- [?_by=Continent&_c=Name|count](flags?_by=Continent&_c=Name|count&_format=table): group by Continent, count names of countries
- [?_by=Continent&_c=Name|count&_c=c1|min&_c=c1|avg&_c=c1|max](flags?_by=Continent&_c=Name|count&_c=c1|min&_c=c1|avg&_c=c1|max&_format=table)
    - `_by=Continent`: group by "Continent"
    - `_c=Name|count`: count values in "Name"
    - `_c=c1|min`: min value of "c1" in each continent
    - `_c=c1|avg`: mean value of "c1" in each continent
    - `_c=c1|max`: max value of "c1" in each continent

You can also aggregate on entire column using empty `?by=`. For example:

- [_by=&_c=c1|avg&_c=c2|count](flags?_by=&_c=c1|avg&_c=c2|count)
- [On SQLite _by=&_c=c3|avg&_c=c2|count&c1>=90](db?_by=&_c=c3|avg&_c=c2|count&c1>=90)

Filters on columns apply BEFORE the grouping. For example:

- [?c1>=80&_by=Continent&_c=Name|count](flags?c1>=80&_by=Continent&_c=Name|count&_format=table): count of countries by continent where c1 > 80

You can also filter AFTER the grouping by filtering with the derived column names. For example:

- [?_by=Continent&_c=Name|count&Name|count>=30](flags?_by=Continent&_c=Name|count&Name|count>=30&_format=table): count of countries by continent where count of countries is > 30

Sorting (`?_sort=`) and pagination (`?_limit=` and `?_offset=`) apply *after* the group by.

- [?_by=Continent&_sort=Continent&_offset=2&_limit=2](flags?_by=Continent&_sort=Continent&_offset=2&_limit=2&_format=table): count of countries by continent sorted by Continent, 2 per page


## FormHandler metadata

When `?_meta=y` is specified, the HTTP headers have additional metadata about the
request and the response. These headers are available:

- `Fh-Data-Count: <number>`: Number of rows in the dataset. Will not be set for databases, only files.
- `Fh-Data-Offset: <number>`: Start row (specified by `?_offset=`). Defaults to 0
- `Fh-Data-Limit: <number>`: Max rows limit (specified by `?_limit=`). Defaults to 0
- `Fh-Data-Filters: <list>`: Applied filters as `[(col, op, val), ...]`. Defaults to `[]`
- `Fh-Data-Ignored: <list>`: Ignored filters as `[(col, vals), ('_sort', col), ('_by': col), ...]`. Defaults to `[]`
- `Fh-Data-Sort: <list>`: Sorted columns as `[(col, True), ...]`. The second parameter is `ascending=`. Defaults to `[]`
- `Fh-Data-Excluded: <list>`: Excluded columns as `[col, ...]`. (TODO: test this)
- `Fh-Data-By`: Group by columns as `[col, ...]`

All values are all JSON encoded.

## FormHandler forms

FormHandler is designed to work without JavaScript. For example:

```html
<form action="flags">
  <p><label><input name="Name~"> Search for country name</label></p>
  <p><label><input name="c1>~" type="number" min="0" max="100"> Min c1 value</label></p>
  <p><label><input name="c1<~" type="number" min="0" max="100"> Max c1 value</label></p>
  <p><select name="_sort">
    <option value="c1">Sort by c1 ascending</option>
    <option value="-c2">Sort by c1 descending</option>
  </select></p>
  <input type="hidden" name="_format" value="html">
  <button type="submit">Filter</button>
</form>
```

<form action="flags">
  <p><label><input name="Name~" value="stan"> Country search</label></p>
  <p><label><input name="c1>~" type="number" min="0" max="100" value="0"> Min c1 value</label></p>
  <p><label><input name="c1<~" type="number" min="0" max="100" value="50"> Max c1 value</label></p>
  <p><select name="_sort">
    <option value="c1">Sort by c1 ascending</option>
    <option value="-c2">Sort by c1 descending</option>
  </select></p>
  <button type="submit">Apply filters</button>
  <input type="hidden" name="_format" value="html">
</form>

This form filters without using any JavaScript code. It applies the URL query
parameters directly.

## FormHandler transforms

FormHandler has 4 ways of transforming the request / data using Python functions.

| Transform                                   | When does it run?               | What does it do?   | What can it accept?                                              |
|---------------------------------------------|---------------------------------|--------------------|------------------------------------------------------------------|
| [prepare](#formhandler-prepare)             | Before loading data             | Replaces arguments | `args`: [handlers.args](../modelhandler/#basehandler-attributes) |
| [queryfunction](#formhandler-queryfunction) | Before loading data             | Replaces DB query  | `args`: [handlers.args](../modelhandler/#basehandler-attributes) |
| [function](#formhandler-functions)          | After loading, before filtering | Replaces data      | `data`: DataFrame of loaded data<br>`handler`: handler           |
| [modify](#formhandler-modify)               | After filtering                 | Replaces result    | `data`: DataFrame of *filtered* data<br>`handler`: handler       |

Click on the links to learn how to use them.

## FormHandler prepare

To modify the arguments before executing the query, use `prepare:`.

```yaml
url:
  replace:
    pattern: /$YAMLURL/replace
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/flags.csv
      prepare: args.update(Cross=args.pop('c', []))
      # Another example:
      # prepare: my_module.calc(args, handler)
```

This `prepare:` method replaces the `?c=` with `?Cross=`. So
[replace?c=Yes](replace?c=Yes&_format=html) is actually the same as
[flags?Cross=Yes](flags?Cross=Yes&_format=html).

`prepare:` is a Python expression that modifies `args`. `args` is a dict
containing the URL query parameters as lists of strings. `?x=1&y=2` becomes is
`{'x': ['1'], 'y': ['2']}`. `args` has [default values](#formhandler-defaults)
merged in. You can modify `args` in-place and return None, or return a value that
replaces `args`.

Some sample uses:

- [Validate inputs](#formhandler-validation)
- Add/modify/delete arguments based on the user. You can access the user ID via
  `handler.current_user` inside the `prepare:` expression
- Add/modify/delete arguments based on external data.
- Replace argument values.


## FormHandler functions

Add `function: ...` to transform the data before filtering. Try this
[example](continent):

```yaml
url:
  continent:
    pattern: /$YAMLURL/continent
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/flags.csv
      function: data.groupby('Continent').sum().reset_index()
      # Another example:
      # function: my_module.calc(data, handler.args)
```

This runs the following steps:

1. Load `flags.csv`
2. Run `function`, which must be an expression that returns a DataFrame. The
   expression can use the variables `data` (loaded DataFrame) and `handler`
   (FormHandler object). You can access URL query parameters via `handler.args`
3. Filter the data using the URL query parameters

That this transforms the data *before filtering*.
e.g. [filtering for c1 > 1000](continent?c1>=1000) filters on the totals, not individual rows.
To transform the data after filtering, use [modify](#formhandler-modify).

`function:` also works with [database queries](#formhandler-query), but loads
the **entire** table before transforming, so ensure that you have enough memory.

## FormHandler modify

You can modify the data returned after filtering using the `modify:` key. Try
this [example](totals):

```yaml
url:
  totals:
    pattern: /$YAMLURL/totals
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/flags.csv
      modify: data.sum(numeric_only=True).to_frame().T
```

This runs the following steps:

1. Load `flags.csv`
2. Filter the data using the URL query parameters
3. Evaluate the `modify:` expression. It can use a DataFrame `data`. The result
   of the expression must be a DataFrame (or dict of DataFrames.)

This transforms the data *after filtering*.
e.g. the [Asia result](totals?Continent=Asia) shows totals only for Asia.
To transform the data before filtering, use [function](#formhandler-functions).

`modify:` also works with [database queries](#formhandler-query).

If you have [multiple datasets](#formhandler-multiple-datasets), `modify:` can
modify all of these datasets -- and join them if required.

[This example](modify-multi?_format=html) has two `modify:` -- the first for a
single query, the second applies on both datasets.

```yaml
url:
  formhandler-modify-multi:
    pattern: /$YAMLURL/modify-multi
    handler: FormHandler
    kwargs:
      symbols:
        url: sqlite:///$YAMLPATH/../datahandler/database.sqlite3
        table: flags
        query: 'SELECT Continent, COUNT(DISTINCT Symbols) AS dsymbols FROM flags GROUP BY Continent'
        # Modify ONLY this query. Adds rank column to symbols dataset
        modify: data.assign(rank=data['dsymbols'].rank())
      colors:
        url: $YAMLPATH/flags.csv
        function: data.groupby('Continent').sum().reset_index()
      # Modify BOTH datasets. data is a dict of DataFrames.
      modify: data['colors'].merge(data['symbols'], on='Continent')
```

`modify:` can be any expression that uses `data`, which is a dict of DataFrames
`{'colors': DataFrame(...), 'symbols': DataFrame(...)`. It can return a single
DataFrame or any dict of DataFrames.

`modify:` can be applied to [FormHandler edit](#formhandler-edits) methods

Below configuration has two `modify:` -- which are called after edit operations.

```yaml
  formhandler-edits-multidata-modify:
    pattern: /$YAMLURL/edits-multidata-modify
    handler: FormHandler
    kwargs:
      csv:
        url: $YAMLPATH/sales-edits.csv
        encoding: utf-8
        id: [city, product]
        modify: len(handler.args.keys())
      sql:
        url: mysql+pymysql://root@$MYSQL_SERVER/DB?charset=utf8
        table: sales
        id: [city, product]
      modify: len(handler.args.keys())
```

`modify:` can be any expression/function that uses `data` -- count of records edited and `handler` --
`handler.args` contains [data submitted]((#formhandler-edits)) by the user.


## FormHandler query

You may also use a `query:` to select data from an SQLAlchemy databases. For example:

```yaml
url:
  query:
    pattern: /$YAMLURL/query
    handler: FormHandler
    kwargs:
      url: sqlite:///$YAMLPATH/database.sqlite3
      query: 'SELECT Continent, COUNT(*) AS num, SUM(c1) FROM flags GROUP BY Continent'
```

... returns the query result. [FormHandler filters](#formhandler-filters) apply
on top of this query. For example:

- [query](query?_format=html) returns data grouped by Continent
- [query?num>=20](query?num>=20&_format=html) ► continents where number of countries > 20

This uses [gramex.cache.query](../cache/#query-caching) behind the scenes. You
can cache the query based on a smaller query or table name by specifying a
`table:` parameter. For example:

```yaml
      table: 'SELECT MAX(date) FROM source'
      query: 'SELECT city, SUM(sales) FROM source GROUP BY city'
```

... will run `query:` only if the result of running `table:` changes. You can
also specify `table: source`. This attempts to automatically check if the table
has changed.

The `table:` parameter also supports query substitutions like `query:`.

**WARNING**:

1. `query` loads the full result into memory. So keep the result small.
2. `query` ignores URL query parameters with spaces. `?group=city name` or
   `?group=city+name` **WON'T** select the `"city name"` column. It will fail --
   to avoid [SQL injection](https://en.wikipedia.org/wiki/SQL_injection) attack.
3. The `query` is passed as-is to the DB driver. Escape strings based on the
   driver. E.g. `... WHERE col LIKE '%.com'` should be `... WHERE col LIKE
   '%%.com'` for [pymysql](http://pymysql.readthedocs.io/en/latest/), since `%`
   is treated as a formatting string.
4. Use the correct SQL flavour. E.g. SQL Server, uses `SELECT TOP 10 FROM table`
   instead of `SELECT * FROM table LIMIT 10`.

## FormHandler queryfile

Instead of entering a `query:` directly, you can point to an SQL file using
``queryfile:``

```yaml
url:
  query:
    pattern: /$YAMLURL/query
    handler: FormHandler
    kwargs:
      url: sqlite:///$YAMLPATH/database.sqlite3
      queryfile: $YAMLPATH/query.sql
```

For example:

- [queryfile](queryfile?_format=html) returns data grouped by Continent
- [queryfile?num>=20](queryfile?num>=20&_format=html) ► continents where number of countries > 20

This is **exactly the same as [FormHandler queries](#formhandler-query)** with
the contents of `query.sql` inserted as a `query:` statement. This is best for
long queries that need to be formatted clearly for readability.

If both `query:` and `queryfile:` are present, `queryfile:` takes priority.

## FormHandler queryfunction

To construct very complex queries that depend on the URL query parameters, use
`queryfunction:` instead of `query:`. This can be any expression that accepts
`args` as a dict of lists, and returns a query string. The query string is
processed like a [query:](#formhandler-query) statement. For example:

```yaml
      queryfunction: mymodule.sales_query(args)
```

... can use a function like this:

```python
def sales_query(args):
    cities = args.get('ct', [])
    if len(cities) > 0:
        vals = ', '.join("'%s'" % pymysql.escape_string(v) for v in cities)
        return 'SELECT * FROM sales WHERE city IN (%s)' % vals
    else:
        return 'SELECT * FROM sales'
```

- `?ct=Paris&ct=Delhi` returns `SELECT * FROM sales WHERE city in ('Paris','Delhi')`.
- `?` returns `SELECT * FROM sales`

The resulting query is treated *exactly* like the `query:` statement. So
further formatting and argument substitution still happens.

In addition to `args`, queryfunction can also use `handler`.

### Preventing SQL injection

`queryfunction:` lets you create custom database queries based on user input.
Gramex cannot ensure that the returned query is safe to execute. To avoid this:

Use a database account with **read-only access**, and only to only the
data that it needs.

Use SQL **parameter substitution** for values wherever possible. For example:

```python
def bad_query_function(args):
    return 'SELECT * FROM table WHERE col={val}'.format(val=args['v'])

def good_query_function(args):
    return 'SELECT * FROM table WHERE col=:v'
    # FormHandler will replace the :v with args['v'] if it is a value
```

If you *must* use args as values, sanitize them. For example, `pymysql.escape_string(var)`:

```python
def safe_query_function(args):
    vals = ', '.join("'%s'" % pymysql.escape_string(v) for v in args['city'])
    return 'SELECT * FROM sales WHERE city IN (%s)' % vals
```

**Never use args outside quotes**, e.g. when referring to column names. Ensure
that the column names are always specified by you. For example:

```python
def bad_query_function(args):
    return 'SELECT {col} FROM table'.format(args['col'][0])

def good_query_function(args):
    # Ensure that only these 2 columns we specify can be included.
    columns = {'sales': 'sales', 'growth': 'growth'}
    return 'SELECT {col} FROM table'.format(columns[args['col'][0]])
```

## FormHandler parameters

FormHandler parameters such as `url:`, `ext:`, `table:`, `query:`, `queryfile:`
and all other kwargs (e.g. `sheet_name`) are formatted using the path arguments
and URL query parameters. This allows users to control where and how FormHandler
picks up data. For example, take this structure:

```yaml
url:
  db-parameters:
    pattern: /db/$YAMLURL/(\w+)/(\w+)   # Maps /db/table to {_0:db, _1:table}
    handler: FormHandler
    kwargs:
      url: sqlite:///$YAMLPATH/{_0}.db  # Use _0 as the DB file name
      query:
        SELECT {group}, COUNT(*)        # ?group= specifies column to group by
        FROM {_1}                       # _1 comes from the path arguments
        WHERE {col}=:val                # ?col= as column, ?val= as val
        GROUP BY {group}
  excel-parameters:
    pattern: /xl/$YAMLURL/(\w+)/(\w+)    # Maps /file/sheet to {_0:file, _1:sheet}
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/{_0}.xlsx          # Use _0 as the file name
      sheet_name: '{_1}'                # Use _1 as the sheet name
```

The URL `/db/data/sales?group=org&col=city&val=London` returns the results of
`SELECT org, COUNT(*) FROM sales GROUP BY org WHERE city=London` running on
`data.db`.

The URL `/xl/sales/revenue` returns the "revenue" sheet from `sales.xlsx`.

The `:val` used above is an SQLAlchemy argument. It is replaced by the value
of `?val=` in values (not in column names or in any other place). This will be
safely formatted by SQL and can contain any value. On the other hand, use
`{arg}` for column names, filenames, etc.

For security, there are 2 constraints:

- The arguments for file URLs should not go outside the specified directory
  (e.g. using `..` or `/`). Sub-directories are fine
- The arguments for SQLAlchemy URLs and queries cannot contain spaces

## FormHandler defaults

To specify default values for arguments, use the `default:` key.

```yaml
url:
  continent:
    pattern: /$YAMLURL/continent
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/flags.csv
      function: data.groupby('Continent').sum().reset_index()
      default:
        _limit: 10                  # By default, limit to 10 rows, i.e. ?_limit=10
        Continent: [Europe, Asia]   # Same as ?Continent=Europe&Continent=Asia
```


## FormHandler validation

The [prepare](#formhandler-prepare) function can raise a HTTPError in case of
invalid inputs. For example, add a `prepare: my_module.validate(args, handler)`
and use this `validate()` function:

```python
# my_module.py
from tornado.web import HTTPError
from gramex.http import BAD_REQUEST

def validate(args, handler):
    if 'city' in args and 'state' not in args:
        raise HTTPError(BAD_REQUEST, 'Cannot use ?city= without ?state=')

    admin = 'admin' in (handler.current_user or {}).get('role', '')
    if 'city' in args and not admin:
        raise HTTPError(BAD_REQUEST, 'Only admins can search by ?city=')
```

This will raise a HTTP 400 Bad Request error if you use `?city=` without
`?state=`, or if a non-admin user requests `?city=`.


## FormHandler multiple datasets

You can return any number of datasets from any number of sources. For example:

```yaml
url:
  multidata:
    pattern: /$YAMLURL/multidata
    handler: FormHandler
    kwargs:
      continents:
        url: $YAMLPATH/flags.csv
        function: data.groupby('Continent').sum().reset_index()
      stripes:
        url: $YAMLPATH/flags.csv
        function: data.groupby('Stripes').sum().reset_index()
```

Multiple datasets as formatted as below:

- [HTML](multidata?_format=html) shows tables one below the other, with a heading
- [CSV](multidata?_format=csv) shows CSV tables one below the other, with a heading
- [XLSX](multidata?_format=xlsx) downloads an Excel file with each sheet as a dataset
- [JSON](multidata?_format=json) returns a dict with each value containing the data.

By default, [filters](#formhandler-filters) apply to all datasets. You can
restrict filters to a single dataset by prefixing it with a `<key>:`. For example:

- [multidata?_limit=2](multidata?_limit=2&_format=html) shows 2 rows on both datasets
- [multidata?stripes:_limit=2](multidata?stripes:_limit=2&_format=html) shows 2 rows only on the stripes dataset

FormHandler runs database filters as co-routines. These queries do not block
other requests, and run across datasets in parallel.

Note:

- If `format:` is specified against multiple datasets, the return value could be
  in any format (unspecified).

## FormHandler directory listing

FormHandler allows listing files in a directory. To set this up, use a `dir://`
URL like this: `url: dir:///path/to/directory`:

```yaml
    pattern: /$YAMLURL/dir
    handler: FormHandler
    kwargs:
      url: dir:///$YAMLPATH          # Point to any directory
```

Here is a sample output:

- [All files in this directory](dir?_format=table&_c=dir&_c=name&_c=size&_c=type)
- [Largest files in this directory](dir?_format=table&_c=dir&_c=name&_c=size&_c=type&_sort=-size)

This URL is interpolatable using arguments as well for example:

```yaml
    pattern: /$YAMLURL/dir/(.*)
    handler: FormHandler
    kwargs:
      url: dir:///$YAMLPATH/{_0}    # /dir/abc points to abc/ under this directory
    # url: dir:///$YAMLPATH/{root}  # /dir/?root=abc points to abc/ under this directory
```

The arguments are escaped and cannot contain `../` and other mechanisms to go
beyond the root directory specified.

## FormHandler templates

The output of FormHandler can be rendered as a custom template using the
`template` format. For example, this creates a ``text`` format:

```yaml
    pattern: text
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/flags.csv
      formats:
        text:
          format: template
          template: $YAMLPATH/text-template.txt
          headers:
              Content-Type: text/plain
```

Here is the output of [?_format=text&_limit=10](flags?_format=text&_limit=10).

The file [$YAMLPATH/text-template.txt](text-template.txt) is rendered as a Gramex
template using the following variables:

- `data`: the DataFrame to render, after filters, sorts, etc. If the handler
  has multiple datasets, `data` is a dict of DataFrames.
- `meta`: dict holding information about the filtered data. If the handler has
  multiple datasets, `meta` is a dict of dicts. It has these keys:
    - `filters`: Applied filters as `[(col, op, val), ...]`
    - `ignored`: Ignored filters as `[(col, vals), ('_sort', vals), ...]`
    - `sort`: Sorted columns as `[(col, True), ...]`. The second parameter is `ascending=`
    - `offset`: Offset as integer. Defaults to 0
    - `limit`: Limit as integer - `None` if limit is not applied
- `handler`: the FormHandler instance

## FormHandler edits

From **v1.23**, FormHandler allows users to add, edit or delete data using the
POST, PUT and GET HTTP operators. For example:

    POST ?id=10&x=1&y=2         # Inserts a new record {id: 10, x: 1, y: 2}
    PUT ?id=10&x=3              # Update x to 3 in the record with id=10
    DELETE ?id=10               # Delete the record with id=10

This requires primary keys to be defined in the FormHandler as follows:

```yaml
    pattern: /$YAMLURL/flags
    handler: FormHandler
    kwargs:
      url: /path/to/flags.csv
      id: ID                  # Primary key column is "ID"
```

You may specify multiple primary keys using a list. For example:

```yaml
      id: [state, city]     # "state" + "city" is the primary key
```

If the `id` columns do not exist in the data, or are not passed in the URL,
it raises 400 Bad Request HTTP Error.

A POST, PUT or DELETE operation immediately writes back to the underlying `url`.
For example, this writes back to an Excel file:

```yaml
      # Saves data to Sheet1 of file.xlsx with plant & machine id as keys
      url: /path/to/file.xlsx
      sheetname: Sheet1
      id: [plant, machine id]
```

This writes back to an Oracle Database:

```yaml
      # Saves to "sales" table of Oracle DB with month, product & city as keys
      # Typically, the primary keys of "sales" should be the same as `id` here
      url: 'oracle://$USER:$PASS@server/db'           # Reads from Oracle
      table: sales
      id: [month, product, city]
```

To add or delete multiple values, repeat the keys. For example:

    POST ?id=10&x=1&y=2 & id=11&x=3&y=4   # Inserts {id:10, x:1, y:2} & {id:11, x:3, y:4}
    DELETE ?id=10 & id=11                 # Delete id=10 & id=11

Note: PUT currently works with single values. In the future, it may update
multiple rows based on multiple ID selections.

If you are using [multiple datasets](#formhandler-multiple-datasets), add an
`id:` list to each dataset. For example:

```yaml
  excel:
      url: /path/to/file.xlsx
      sheetname: Sheet1
      id: [plant, machine id]
  oracle:
      url: 'oracle://$USER:$PASS@server/db'
      table: sales
      id: [month, product, city]
```

In the URL query, prefix by the relevant dataset name. For example this updates
only the `continents:` dataset:

    POST ?continents:country=India&continents:population=123123232
    PUT ?continents:country=India&continents:population=123123232
    DELETE ?continents:country=India

All operators set a a `Count-<datasetname>` HTTP header that indicates the number
of rows matched by the query:

    Count-Data: <n>     # Number of rows matched for data: dataset

If [redirect:](../config/#redirection) is specified, the browser is redirected to
that URL (only for POST, PUT or DELETE, not GET requests). If no redirect is
specified, these methods return a JSON dict with 2 keys:

- `ignored`: Ignored columns as `[(col, vals), ]`
- `filters`: Applied filters as `[(col, op, val), ...]` (this is always an empty list for POST)

### FormHandler POST

This form adds a row to the data.

```html
<!-- flags.csv has ID, Name, Text and many other fields -->
<form action="flags-add" method="POST" enctype="multipart/form-data">
  <label for="ID">ID</label>     <input type="text" name="ID" value="XXX">
  <label for="Name">Name</label> <input type="text" name="Name" value="New country">
  <label for="Text">Text</label> <input type="text" name="Text" value="New text">
  <input type="hidden" name="_xsrf" value="{{ handler.xsrf_token }}">
  <button type="submit" class="btn btn-submit">Submit</button>
</form>
```

We need to specify a primary key. This YAML config specifies `ID` as the primary key.

```yaml
      id: ID        # Make ID the primary key
```

When the HTML `form` is submitted, field names map to column names in the data.
For example, `ID`, `Name` and `Text` are columns in the flags table.

You can insert multiple rows. The number of rows inserted is returned in the
`Count-<dataset>` header.

The form can also be submitted via AJAX. See [FormHandler PUT](#formhandler-put)
for an AJAX example.

### FormHandler PUT

This PUT request updates an existing row in the data.

```js
// flags.csv has ID, Name, Text and many other fields
$.ajax('flags-edit', {
  method: 'PUT',
  headers: xsrf_token,      // See documentation on XSRF tokens
  data: {ID: 'XXX', Name: 'Country 1', Text: 'Text ' + Math.random()}
})
```

We need to specify a primary key. This YAML config specifies `ID` as the primary key.

```yaml
      id: ID        # Make ID the primary key
```

When the HTML `form` is submitted, existing rows with ID `XXX` will be updated.

The number of rows changed is returned in the `Count-<dataset>` header.

If the key is missing, PUT currently returns a `Count-<dataset>: 0` and does not
insert a row. This behaviour may be configurable in future releases.

When the HTML `form` is submitted, field names map to column names in the data.
For example, `ID`, `Name` and `Text` are columns in the flags table.

The form can also be submitted directly via a HTML form.
See [FormHandler POST](#formhandler-post) for a HTML example.
The `?x-http-method-override=PUT` overrides the method to use PUT. You can
also use the HTTP header `X-HTTP-Method-Override: PUT`.

### FormHandler DELETE

This DELETE request deletes existing rows in the data.

```html
<!-- flags.csv has Name as a column -->
<form action="flags-delete" method="POST" enctype="multipart/form-data">
  <input type="hidden" name="x-http-method-override" value="DELETE">
  <label for="Name">Name</label> <input type="checkbox" name="Name" value="Country 1" checked>
  <label for="Name">Name</label> <input type="checkbox" name="Name" value="Country 2">
  <button type="submit" class="btn btn-submit">Submit</button>
</form>
```

When the HTML `form` is submitted, existing rows with Name `Country 1` will be
deleted. This is because only `Country 1` is checked by default. The user can
uncheck it and check `Country 2`. On submission, only `Country 2` is deleted.

The number of rows deleted is returned in the `Count-<dataset>` header.

The form can also be submitted via AJAX. See [FormHandler PUT](#formhandler-put)
for an AJAX example.

Note:

- The keys specified act like a filter or a `where` clause, deleting all rows that match
- If the filters do not match any rows, it does not throw any error.
- `?x-http-method-override=DELETE` overrides the method to use DELETE. You can
  also use the HTTP header `X-HTTP-Method-Override: DELETE`.

## FormHandler JSON body

**v1.34**. Arguments to the
[POST](#formhandler-post),
[PUT](#formhandler-put), and
[DELETE](#formhandler-delete) methods
can send a `Content-Type: application/json`.
This allows passing JSON data as arguments. The values must be sent as arrays.

For example, `?x=1&y=2` must be sent as `{"x": ["1"], "y": ["2"]}`.

These two approaches are the same:

```js
// Send using `application/www-url-form-encoded` or `multipart/form-data`
$.ajax('flags-edit', {
  method: 'PUT',
  headers: xsrf_token,      // See documentation on XSRF tokens
  data: {ID: 'XXX', Name: 'Country 1'}
})

// Send using `application/json`
$.ajax('flags-edit', {
  method: 'PUT',
  contentType: 'application/json',
  dataType: 'json',
  headers: xsrf_token,      // See documentation on XSRF tokens
  data: JSON.stringify({ID: ['XXX'], Name: ['Country 1']})    // Note: values are arrays
})
```

When using jQuery, the former is easier. But when using
[fetch](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)
or other AJAX / server-side libraries, `application/json` may be easier.

```js
fetch('flags-edit', {
  method: 'POST',
  headers: {'content-type': 'application/json'},
  body: JSON.stringify({ID: ['XXX'], Name: ['Country 1']})    // Note: values are arrays
})
```

### Custom HTTP Headers

The `url.<url>.kwargs` section accepts a `headers:` key. So does `url.kwargs.formats.<format>`.
This sets custom HTTP headers. For example, to access a
[FormHandler JSON response](flags?_format=cors-json) via AJAX from a different
server, add the CORS `Access-Control-Allow-Origin` headers.

```yaml
pattern: /$YAMLURL/flags
handler: FormHandler
kwargs:
    ...
  formats:
    ...
    cors-json:
      format: json
      headers:
        Content-Type: application/json    # Display as json
        Access-Control-Allow-Origin: '*'  # Allow CORS (all servers can access via AJAX)
  headers:
    Cache-Control: public, max-age=3600   # All formats are cached for 1 hour
```

[formhandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.FormHandler
