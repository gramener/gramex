---
title: Form Handler Filtering data with ease
prefix: Tip
...

Gramex 1.21 has a powerful handler called [FormHandler](../formhandler/). This makes it easy to render data. You can stop writing FunctionHandler to do this.

## Read data from files

You can just point to a CSV, XLSX or HDF file.

    :::yaml
    handler: FormHandler
    kwargs:
        url: $YAMLPATH/flags.csv

The result looks like [this](../formhandler/flags)

## Perform calculations

If you want to return data after performing calculations, add a function:

    :::yaml
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/flags.csv
      function: mymodule.myfunction(data)

This uses the results of mymodule.myfunction(data) instead of data.

## Read data from databases

Just change the URL from the file to an SQLAlchemy URL. You need to specify a table. You can optionally add a query.

    :::yaml
    url: 'mysql+pymysql://$USER:$PASS@server/db'
    table: sales
    query: 'SELECT * FROM sales ORDER BY date DESC'

    url: 'mssql+pyodbc://$USER:$PASS@dsn'
    table: sales
    query: 'SELECT TOP 1000 * FROM sales'

    url: 'sqlite:///D:/path/to/file.db'
    table: sales

## Filter with ease

[?Continent=Europe](../formhandler/flags?Continent=Europe&_format=html) shows rows where Continent = Europe
[?Continent!=Europe](../formhandler/flags?Continent!=Europe&_format=html) - where Continent is NOT Europe
[?Name~=United](../formhandler/flags?Name~=United&_format=html) - where name contains "United"

... and many more [filter operations](../formhandler/#formhandler-filters).

## Choose your format

You can return the data as [HTML](../formhandler/flags?_format=html), [CSV](../formhandler/flags?_format=csv), [JSON](../formhandler/flags?_format=json), or [XLSX](../formhandler/flags?_format=xlsx). Formatted XLSX (with conditional formatting, etc) will be available in the next release of Gramex.

You should be able to replace most of your FunctionHandlers with [FormHandler](../formhandler/). Please reach out to the CTO team if you have questions.
