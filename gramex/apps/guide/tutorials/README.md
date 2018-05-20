---
title: FormHandler tutorial
...

[TOC]

FormHandler allows you to read and write from files and databases.

## Usecase: Retail sales tracker

Consider an application that tracks sales of an organization in different regions.
The dashboard shows the sales of different products in different regions with
options to select multiple date ranges including by week/month/custom date ranges.
In order to support the application, client shares the data in CSV format.

We use FormHandler capabilties to (read the data, process incoming requests
including date selections, modify the output) to create the building blocks of
the application.

## Read data from different Sources

### From file

To expose `data.csv` under `/data` URL use

```YAML
  app/file/data:
    # maps to /data request
    pattern: $YAMLURL/data
    handler: FormHandler
    kwargs:
      url: $YAMLURL/data.csv     # gramex.cache.open uses pandas.read_csv
      delimiter: '|'             # for non-comma delimiter
```

You can read from multiple file formats: `CSV`, `XLSX`, `HDF`, `JSON`.
If `XLSX` is mentioned, it accepts an optional parameter: `sheetname`.

```YAML
  app/file/data:
    # maps to /data-xlsx request for XLSX data source
    pattern: $YAMLURL/data-xlsx
    handler: FormHandler
    kwargs:
      url: $YAMLURL/flags.xlsx
      sheetname: countries
```

Additionally, a file with no extension can be passed with `ext` parameter.

```YAML
  app/file/data:
    pattern: $YAMLURL/data
    handler: FormHandler
    kwargs:
      url: $YAMLURL/flags
      ext: xlsx
```

Internally, files are read via `pandas.read_*` methods. These methods accepts
many parameters which can be configured as attributes in `YAML`.

### Reading from Databases

Any valid `SQLAlchemy` URL is Formhandler to read from SQL databases.

```YAML
  app/file/databases:
    # maps to /database request
    pattern: $YAMLURL/database
    handler: FormHandler
    kwargs:
      url: 'mysql+pymysql://$USER:$PASSWORD@server/db'        # MySQL
      # url: 'postgres://$USER:$PASSWORD@server/db'           # PostgreSQL
      # url: 'oracle://$USER:$PASSWORD@server/db'             # Oracle
      # url: 'mysql+pyodbc://$USER:$PASSWORD@dsn'             # MS SQL
      # url: 'sqlite:///path/to/file.db'                      # SQLite
      table: sales
```

### Safe practices with Databases

- Do not directly define usernames and passwords in YAML configuration.
Use environment variables.
- Cache your data requests via cache-control headers. [Documentation](../cache/).
- Prepare the arguments
- URL parameters are not always in the required format that the data source expects.
Use FormHandler's `prepare` option lets the user manipulate the URL parameters to suit the application needs.
    - For example, parse month from date before querying.
    Assume parameter from the URL request is: month (number).
    But the query expects the format to be in month name (string format).
    Data source can have many columns including names such as `State name` and `Month`.

Request: `/data?s=telangana&m=3`

Example: `prepare` parameters in `YAML`

```YAML
  app/data:
    # maps to /data?m=3&s=telangana request
    pattern: $YAMLURL/data
    handler: FormHandler
    kwargs:
      url: $YAMLURL/data.csv
      prepare: args.update(State_name=args.pop('s', []))
```

Example: `prepare` parameters via function

```YAML
  app/data:
    pattern: $YAMLURL/data
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/data.csv
      prepare: app.prepare(args, handler)
```

Corresponding python function

```python
import calendar

def prepare(args, handler):
  """Convert month number to month name."""
  month = calendar.month_name[args.get('m')]
  args.update({
    'm': [month]
  })
  return args
```

Perform data operations

```YAML
  app/data:
    pattern: $YAMLURL/data
    handler: FormHandler
    kwargs:
      url: $YAMLPATH/data.csv
      prepare: app.prepare(args, handler)
      function: data.groupby(‘Month’)
```

## Query option

```YAML
app/data/query:
  pattern: $YAMLURL/data-query
  kwargs:
    url: $YAMLURL/flags.sqlite
    # query should be a SQLAlchemy database supported string
    query: 'SELECT * FROM flags LIMIT 5'
```

## Queryfile option

```YAML
app/data/queryfile:
  pattern: $YAMLURL/data-queryfile
  kwargs:
    url: $YAMLURL/flags.sqlite
    # query should be a SQLAlchemy database supported string
    queryfile: $YAMLPATH/query.sql
```

This result will contain first `10000` rows by default.
To increase/decrease this limit, specify `_limit` parameter using `?_limit=15000`


## Modify the result
Data returned post filtering by FormHandler can be changed via modify option.
To modify result after executing the query.

Example: `modify` parameters in YAML

```YAML
app/data/modify:
  pattern: $YAMLURL/data-modify
  kwargs:
    url: $YAMLURL/flags.sqlite
    modify: data.sum(numeric_only=True).to_frame().T
```

Example: `modify` parameters in python function

```YAML
replace:
  pattern: /$YAMLURL/replace
  handler: FormHandler
  prepare: app.prepare
  query: "SELECT * FROM flags LIMIT 5"
  modify: app.modify(data)
```

Corresponding python function

```python
def modify(data):
    return data.sum(numeric_only=True).to_frame().T
```

Visit FormHandler related [documentation](../formhandler/) for additional details.
