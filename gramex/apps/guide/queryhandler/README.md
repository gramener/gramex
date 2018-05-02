---
title: QueryHandler runs SQL queries
prefix: QueryHandler
...

From **v1.23** QueryHandler is deprecated. Use [FormHandler](../formhandler/).

[TOC]

`QueryHandler` fetches data from SQL databases and returns the results as CSV,
JSON, or HTML tables. Here is a sample configuration that browses [gorilla genes](genome?format=html&limit=10):

    :::yaml
    url:
        genome:
            pattern: /genome
            handler: QueryHandler
            kwargs:
                url: 'mysql+pymysql://anonymous@ensembldb.ensembl.org/gorilla_gorilla_core_84_31'
                sql: 'SELECT * FROM gene'

(This uses the public [ensemble gene database](http://ensembldb.ensembl.org/info/data/mysql.html).)

Here's a similar configuration for [flags data](flags):

    :::yaml
    url:
        flags:
            pattern: /$YAMLURL/flags                # The "/flags" URL...
            handler: QueryHandler                   # uses QueryHandler
            kwargs:
                url: sqlite:///database.sqlite3     # SQLAlchemy database URL
                sql: >                              # Run this (multi-line) SQL query on database
                    SELECT * FROM flags
                    WHERE continent=:continent
                    AND c1>:c1
                default:
                    continent: Africa               # By default, :continent is Africa
                    limit: 10                       # By default, display 10 rows
                    format: html                    # By default, render as html (can be json/csv/xlsx)
                query:
                  c1: 10                            # :c1 is always forced to 10

This displays African flags. The SQL query can contain parameters (e.g.
`:continent`, `:c1`, etc.) The `default:` section defines their default values --
similar to [DataHandler default](../datahandler/#datahandler-defaults).

You can specify the default `limit:` (number of rows) in the response.

The `format:` key can be `html`, `csv`, `xlsx`, `json` or `template` -- see
[DataHandler formats](../datahandler/#datahandler-formats). You can specify the
output as a downloadable file with a filename, e.g. `test.csv` in the example here:

    :::yaml
        kwargs:                         # Add this entry under the handler kwargs:
            ...
            query: {format: csv}            # Freeze CSV as the format
            default: {filename: test.csv}   # Set the default filename

URL query parameters can override these. For example:

- [flags?continent=Europe](flags?continent=Europe) shows flags for Europe
- [flags?format=json](flags?format=json) renders the flags in JSON
- [flags?format=csv&filename=flags.csv](flags?format=csv&filename=flags.csv) downloads `flags.csv`
- [flags?limit=20](flags?limit=20) shows 20 rows instead of the default 10

Here's the JSON output:

    :::js
    $.get('flags?format=json&limit=2')
    // OUTPUT

The `query:` section freezes these values, and they cannot be overridden by the
URL query parameters. For example:

- [flags?c1=0](flags?c1=0) will not filter for `c1=0` -- the `query:` section has
  frozen this value at 10.

## QueryHandler templates

QueryHandler templates are like [DataHandler templates](../datahandler/#datahandler-templates).
You can render the data output in any form.

Here is the default output of [flags?format=template](flags?format=template).

You can specify a custom template file as `template: $YAMLPATH/template.html`
under `kwargs:`. This template is passed the following variables:

- `handler`: The QueryHandler instance
- `query`: An sqlalchemy TextClause. Convert to `str(query)` to get the text query
- `data`: The DataFrame that has the result

In case of [Multiple SQL queries](#multiple-sql-queries), the template is passed:

- `handler`: The QueryHandler instance
- Each query key is passed as a variable. Its value is a dict with:
    - `query`: An sqlalchemy TextClause. Convert to `str(query)` to get the text query
    - `data`: The DataFrame that has the result for this key

To iterate over the list of keys in the query, use ``handler.result``.

## QueryHandler POST

You can write INSERT / UPDATE / DELETE queries. For example:

    :::yaml
    url:
        update:
            pattern: /$YAMLURL/update               # The update URL
            handler: QueryHandler                   # uses QueryHandler
            kwargs:
                url: sqlite:///$YAMLPATH/../datahandler/database.sqlite3    # to connect database at this path/url
                sql: UPDATE points SET y=:y WHERE x >= :x                   # Run this query

You need to use the `POST` HTTP when running these queries. (`GET` may run the
SQL query but will return an error.)

A successful query returns a HTTP 200 with empty results.

    :::js
    $.ajax('update', {
      method: 'POST',               // Run the update query
      traditional: true,            // Required when using $.ajax
      data: {x: 9, y: 12}           // Where x >= 9, set y values to 12
    })
    // OUTPUT

Now let's see the data. You will find that `y` is 12 for all values of x >= 9.

    :::js
    $.get('update-values?x=9')       // fetch values where x >= 9
    // OUTPUT


## Multiple SQL queries

You can create a dictionary of multiple SQL queries. For example:

    :::yaml
    url:
        flags:
            pattern: /$YAMLURL/multi                # The /multi URL...
            handler: QueryHandler                   # uses QueryHandler
            kwargs:
                url: sqlite:///database.sqlite3     # SQLAlchemy database URL
                sql:
                    europe: 'SELECT ID, Name, Continent FROM flags WHERE Continent="Europe"'
                    vertical-stripes: 'SELECT * FROM flags WHERE Stripes="Vertical"'
                    reddish: 'SELECT COUNT(*) AS count_of_red_flags FROM flags WHERE c1>50'

The [result](multi) appears in:

- [CSV](multi?format=csv) as tables with headings, separated by a blank line
- [HTML](multi?format=html) as tables with headings
- [JSON](multi?format=json) as an object. The `sql:` keys are the keys, the values hold the data
- [XLSX](multi?format=xlsx) as sheets. The sheet name is the `sql:` key
- [data.xlsx](multi?format=xlsx&filename=data.xlsx) as sheets. The download file name is `data.xlsx`

Every parameter and arguments is applicable for each query. The results are
always in the same order as in the `sql:` config.

<script src="https://cdnjs.cloudflare.com/ajax/libs/cookie.js/1.2.0/cookie.min.js"></script>
<script src="../datahandler/show-output.js"></script>
