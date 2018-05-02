---
title: DataHandler connects to data
prefix: DataHandler
...

From **v1.23** DataHandler is deprecated. Use [FormHandler](../formhandler/).

[TOC]

`DataHandler` let's you fetch data from files and databases, and returns the
result as CSV, JSON, XLSX or HTML tables. Here is a sample configuration that
browses [gorilla genes](genome?format=html&limit=10):

    :::yaml
    url:
        genome-data:
            pattern: /genome
            handler: DataHandler
            kwargs:
                driver: sqlalchemy
                url: mysql+pymysql://anonymous@ensembldb.ensembl.org/gorilla_gorilla_core_84_31
                table: gene

(This uses the public [ensemble gene database](http://ensembldb.ensembl.org/info/data/mysql.html).)

## DataHandler on sqlite3

To start you off, there's a `database.sqlite3` in this application folder.
(Gramex downloaded [flags data](https://gramener.com/flags/) on startup. See
[dbsetup.flags()](dbsetup.py) and the scheduler in [gramex.yaml](gramex.yaml).

The `DataHandler` below exposes the flags table in `database.sqlite3` at the URL [flags](flags).

    :::yaml
    flags:
      pattern: /$YAMLURL/flags                # The URL flags
      handler: DataHandler                    # uses DataHandler
      kwargs:
          driver: blaze                               # with blaze or sqlalchemy driver
          url: sqlite:///$YAMLPATH/database.sqlite3   # to connect database at this path/url
          table: flags                                # on this table
          parameters: {encoding: utf8}                # with additional parameters provided
          thread: false                               # Disable threading if you see weird bugs
          default:
              format: html                            # Can also be json, csv, xlsx

## DataHandler usage

Once we have this setup, we can query the data with a combination of parameters like `select`, `where`, `groupby`, `agg`, `offset`, `limit`, `sort`

- `select` retrieves specific columns. E.g.
  [?select=Name&select=Continent](flags?select=Name&select=Continent)
- `where` filters the data. E.g.
  [?where=Stripes=Vertical](flags?where=Stripes==Vertical). You can use the
  operators `=` `&gt;=` `&lt;=` `&gt;` `&lt;` `!=`. Multiple conditions can be
  applied. E.g.
  [where=Continent=Asia&where=c1>50](flags?where=Continent=Asia&where=c1>50)
- `group` to group records on columns and aggregate them. E.g.
  [?groupby=Continent&agg=c1:sum(c1)](flags?groupby=Continent&agg=c1:sum(c1))
- `agg` - return a single value on grouped collection. Supported aggregations
  include `min`, `max`, `sum`, `count`, `mean` and `nunique`. E.g.
  [groupby=Continent&agg=nshapes:nunique(Shapes)](flags?groupby=Continent&agg=nshapes:nunique(Shapes))
- `limit` - limits the result to n number of records. By default, the first 100
  rows are displayed. E.g. [?limit=5](flags?limit=5) shows the first 5 rows.
- `offset` - excludes the first n number of records. E.g.
  [?offset=5&limit=5](flags?offset=5&limit=5) shows the next 5 rows
- `sort` - sorts the records on a column in ascending order by default. You can
  change the order with the `:asc` / `:desc` suffixes. E.g.
  [?sort=Symbols:desc](flags?sort=Symbols:desc)
- `format` - determines the output format. Can be `html`, `json`, `csv`, `xlsx`,
  `template`. E.g. [?format=json](flags?format=json)
- `count` - set to any value to send an `X-Count` HTTP header to the number of
  rows in the query, ignoring `limit` and `offset`.
- `q` searches in all text columns for the string. (If you use `group`, columns
  are searched *after grouping*.)

Examples:

- [?groupby=Continent&agg=count:nunique(Name)&agg=shapes:count(Shapes)&sort=count:desc&q=america](flags?groupby=Continent&agg=count:nunique(Name)&agg=shapes:count(Shapes)&sort=count:desc&q=america):
  For every American continent, show the number of unique countries and the
  number of countries with shapes.

## DataHandler on files

DataHandler can expose data from files. For example:

    :::yaml
    flags-csv:
      pattern: /$YAMLURL/flags-csv
      handler: DataHandler
      kwargs:
          driver: blaze
          url: $YAMLPATH/flags.csv
          parameters: {encoding: utf8}

Once we have this setup, we can query the data with a combination of parameters
like `select`, `where`, `groupby`, `agg`, `offset`, `limit`, `sort`

- `select` retrieves specific columns. E.g.
  [?select=Name&select=Continent](flags-csv?select=Name&select=Continent)
- `where` filters the data. E.g.
  [?where=Stripes=Vertical](flags-csv?where=Stripes==Vertical). You can use the
  operators `=` `&gt;=` `&lt;=` `&gt;` `&lt;` `!=`. Multiple conditions can be
  applied. E.g.
  [where=Continent=Asia&where=c1>50](flags-csv?where=Continent=Asia&where=c1>50)
- `group` to group records on columns and aggregate them. E.g.
  [?groupby=Continent&agg=c1:sum(c1)](flags-csv?groupby=Continent&agg=c1:sum(c1))
- etc. See [DataHandler usage](#datahandler-usage)

## DataHandler on databases

Here are some examples of DataHandler ``kwargs`` to connect to databases:

    # MySQL root on localhost
    kwargs:
        driver: sqlalchemy
        url: mysql+pymysql://root@localhost/database
        table: tablename

    # MySQL user / password on any server
    kwargs:
        driver: sqlalchemy
        url: mysql+pymysql://username:password@servername/database
        table: tablename

    # PostgreSQL user / password on any server
    kwargs:
        driver: sqlalchemy
        url: postgresql://username:password@servername/database
        table: tablename

    # SQL Server (via ODBC) user / password on any server
    kwargs:
        driver: sqlalchemy
        url: mssql+pyodbc://username:password@odbc-connection-name

**A note on threading**. By default, DataHandler runs the query in a separate
thread. However, this code is not currently stable. If you find tables that seem
to be missing columns, or errors that are not reproducible, use `thread: false`
to disable threading (as of v1.13.) Upcoming versions will fix threading issues.

## DataHandler defaults

These parameters can be specified specified in the URL. But you can also set
these as defaults. For example, adding this section under `kwargs:` ensures that
the default format is HTML and the default limit is 10 -- but the URL can
override it.

    :::yaml
    default:
        format: html
        limit: 10

You can make the parameters non-over-ridable using `query:` instead of
`default:`. For example, this section forces the format to html, irrespective of
what the `?format=` value is. However, `?limit=` will override the default of 10.

    :::yaml
    query:
        format: html
    default:
        limit: 10

## DataHandler templates

The output of DataHandler can be rendered as a custom template using the
`template` format. This can be used to create custom forms, render data as
charts, or any other customised data rendering.

Here is the default output of [?format=template](flags?format=template).

You can specify a custom template using the `template:` key. See the example below.

<div class="example">
  <a class="example-demo" href="template/">DataHandler Template example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/datahandler/template/">Source</a>
</div>

The data and handler are passed to the template in variables called ``data`` and
``handler``. You can render these variables in any format.

If the template is not HTML, set [custom HTTP headers](../config/#custom-http-headers)
to specify the correct `Content-Type`.

## Database edits

You can use the `POST`, `PUT` and `DELETE` methods to add, update or delete rows
in a database using DataHandler.

(The examples below use [jQuery.ajax][jquery-ajax] and the [cookie.js][cookie.js] libraries.)

[jquery-ajax]: http://api.jquery.com/jquery.ajax/
[cookie.js]: https://github.com/florian/cookie.js

<script src="https://cdnjs.cloudflare.com/ajax/libs/cookie.js/1.2.0/cookie.min.js"></script>

### DataHandler insert

`POST` creates a new row. You can specify the `val` parameter with one or module
`column=value` expressions. For example, this inserts a row with the `Name`
column as `United Asian Kingdom` and `ID` of `UAK`:

    :::js
    $.ajax('flags', {
      method: 'POST',                     // Add a new rows
      traditional: true,                  // Required when using $.ajax
      data: {
        val: [
          'Name=United Asian Kingdom',    // Name column is United Asian Kingdom
          'ID=UAK'                        // ID column is UAK
        ]
      }
    })
    // OUTPUT

### DataHandler update

`PUT` updates existing rows. The `where` parameter selects the rows to be
updated. The `val` parameter defines the values to be updated. For example, this
updates all rows where the `ID` is `UAK` and sets the `Content` and `Text`
columns:

    :::js
    $.ajax('flags', {
      method: 'PUT',                      // Update one or more rows
      traditional: true,                  // Required when using $.ajax
      data: {
        where: 'ID=UAK',                  // Update the rows where ID is UAK
        val: [
          'Continent=Asia',               // Continent column is set to Asia
          'Text=Mottos'                   // Text column is set to Mottos
        ]
      }
    })

Here is the output of the updated row:

    :::js
    $.ajax('flags', {
      method: 'GET',
      data: {where: 'ID=UAK', format: 'json'}
    })
    // OUTPUT

### DataHandler delete

`DELETE` deletes existing rows. The `where` parameter selects the rows to be
deleted. For example, this deletes all rows where the `ID` is `UAK`:

    :::js
    $.ajax('flags', {
      method: 'DELETE',               // Delete all rows
      data: {
        where: 'ID=UAK',              // where the ID column is UAK
        where: 'Continent=Asia'       // AND the Content column is Asia
      }
    })

### DataHandler formats

By default, DataHandler renders data as JSON. You can override that with the
`format` config. For example, consider the [flags](flags?format=html&limit=10).
By default, the format can be overridden by the URL. For example:

- [flags?format=html](flags?format=html) renders as HTML
- [flags?format=json](flags?format=json) renders as JSON
- [flags?format=csv](flags?format=csv) renders as a CSV download (named `file.csv` by default)
- [flags?format=csv&filename=data.csv](flags?format=csv&filename=data.csv) downloads as `data.csv`
- [flags?format=xlsx](flags?format=xlsx) renders as an Excel download (named `file.xlsx` by default)

The default format is JSON. Change it using [datahandler defaults](#datahandler-defaults).
In this example, the default format is HTML, but the URL can override it.

    :::yaml
        kwargs:                         # Add this entry under the handler kwargs:
            ...
            default: {format: html}     # Change default to HTML

In this example, the format is always CSV. The file will be downloaded as
`test.csv` by default, but can be overridden using the `?filename=` query.

    :::yaml
        kwargs:                         # Add this entry under the handler kwargs:
            ...
            query: {format: csv}            # Freeze CSV as the format
            default: {filename: test.csv}   # Set the default filename

<script src="show-output.js"></script>
