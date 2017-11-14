title: Gramex connects to data

[TOC]

`FormHandler` lets you read & write data from files and databases.

Here is a sample configuration to read data from a CSV file:

    :::yaml
    url:
      flags:
        pattern: /$YAMLURL/flags
        handler: FormHandler
        kwargs:
          url: $YAMLPATH/flags.csv

You can read from multiple file formats as well as databases. The URL may be a
[gramex.cache.open](../cache/#data-caching) path. For example:

    :::yaml
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

Additional parameters like `delimiter:`, `ext:`, etc are passed to
[gramex.cache.open](../cache/#data-caching), which uses the Pandas ``read_*``
methods.

`url:` can also be an SQLAlchemy URL. For example:

    :::yaml
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

    :::yaml
    import:
      path: $GRAMEXPATH/apps/formhandler/gramex.yaml
      YAMLURL: $YAMLURL         # Mount this app at the current folder

You can also create custom PPTX downloads using FormHandler. For example, this
configuration adds a custom PPTX format called `pptx-table`:

    :::yaml
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

- Download the output at [flags?_format=pptx-table](flags?_format=pptx-table&_limit=10&_c=ID&_c=Name&_c=Continent&_c=Stripes).
- Download the [input.pptx](input.pptx) used as a template

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

Note: You can use `FormHandler` to render specific columns in navbar filters using `?_c=`.

## FormHandler forms

FormHandler is designed to work without JavaScript. For example:

    :::html
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

## FormHandler functions

Add `function: ...` to transform the data before filtering. Try this
[example](continent):

    :::yaml
    url:
      continent:
        pattern: /$YAMLURL/continent
        handler: FormHandler
        kwargs:
          url: $YAMLPATH/flags.csv
          function: data.groupby('Continent').sum().reset_index()
          # Another example:
          # function: my_module.calc(data, handler)

This runs the following steps:

1. Load `flags.csv`
2. Run `function`, which must be an expression that returns a DataFrame. The
   input data is a DataFrame called `data`.
3. Filter the data using the URL query parameters

That this transforms the data *before filtering*.
e.g. [filtering for c1 > 1000](continent?c1>=1000) filters on the totals, not individual rows.
To transform the data after filtering, use [modify](#formhandler-modify).

`function:` also works with [database queries](#formhandler-query), but loads
the **entire** table before transforming, so ensure that you have enough memory.

## FormHandler modify

You can modify the data returned after filtering using the `modify:` key. Try
this [example](totals):

    :::yaml
    url:
      totals:
        pattern: /$YAMLURL/totals
        handler: FormHandler
        kwargs:
          url: $YAMLPATH/flags.csv
          modify: data.sum(numeric_only=True).to_frame().T
          # Another example:
          # modify: my_module.calc(data, handler)

This runs the following steps:

1. Load `flags.csv`
2. Filter the data using the URL query parameters
3. Run `function`, which must be an expression that returns a DataFrame. The
   filtered data is a DataFrame called `data`.

This transforms the data *after filtering*.
e.g. the [Asia result](totals?Continent=Asia) shows totals only for Asia.
To transform the data before filtering, use [function](#formhandler-functions).

`modify:` also works with [database queries](#formhandler-query).

## FormHandler query

You may also use a `query:` to select data from an SQLAlchemy databases. For example:

    :::yaml
    url:
      query:
        pattern: /$YAMLURL/query
        handler: FormHandler
        kwargs:
          url: sqlite:///$YAMLPATH/database.sqlite3
          query: 'SELECT Continent, COUNT(*) AS num, SUM(c1) FROM flags GROUP BY Continent'

... returns the query result. [FormHandler filters](#formhandler-filters) apply
on top of this query. For example:

- [query](query?_format=html) returns data grouped by Continent
- [query?num>=20](query?num>=20&_format=html) ► continents where number of countries > 20

The query string is formatted using the arguments using `{arg}` and `:arg`. For
example:

    :::yaml
          query: 'SELECT {group}, COUNT(*) FROM table GROUP BY {group} WHERE state=:state'

will group by whatever is passed as `?group=` and where the state is `?state=`.
For example, `?group=city&state=AR` returns `SELECT city, COUNT(*) FROM table
GROUP BY city WHERE state="AR"`.

`:arg` can only be used as values, not column names or in any other place. This
will be safely formatted by SQL and can contain any value. Use `{arg}` for column
names. This cannot contain spaces.

This uses [gramex.cache.query](../cache/#query-caching) behind the scenes. You
can cache the query based on a smaller query or table name by specifying a
`table:` parameter. For example:

    :::yaml
          table: 'SELECT MAX(date) FROM source'
          query: 'SELECT city, SUM(sales) FROM source GROUP BY city'

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

## FormHandler queryfunction

To construct very complex queries that depend on the URL query parameters, use
`queryfunction:` instead of `query:`. This can be any expression that accepts
`args` as a dict of lists, and returns a query string. The query string is
processed like a [query:](#formhandler-query) statement. For example:

    :::yaml
          queryfunction: mymodule.sales_query(args)

... can use a function like this:

    :::python
    def sales_query(args):
        cities = args.get('ct', [])
        if len(cities) > 0:
            vals = ', '.join("'%s'" % pymysql.escape_string(v) for v in cities)
            return 'SELECT * FROM sales WHERE city IN (%s)' % vals
        else:
            return 'SELECT * FROM sales'

- `?ct=Paris&ct=Delhi` returns `SELECT * FROM sales WHERE city in ('Paris','Delhi')`.
- `?` returns `SELECT * FROM sales`

The resulting query is treated *exactly* like the `query:` statement. So
further formatting and argument subsitition still happens.

In addition to `args`, queryfunction can also use `handler`.

### Preventing SQL injection

`queryfunction:` lets you create custom database queries based on user input.
Gramex cannot ensure that the returned query is safe to execute. To avoid this:

Use a database account with **read-only access**, and only to only the
data that it needs.

Use SQL **parameter substitution** for values wherever possible. For example:

    :::python
    def bad_query_function(args):
        return 'SELECT * FROM table WHERE col={val}'.format(val=args['v'])

    def good_query_function(args):
        return 'SELECT * FROM table WHERE col=:v'
        # FormHandler will replace the :v with args['v'] if it is a value

If you *must* use args as values, sanitize them. For example, `pymysql.escape_string(var)`:

    :::python
    def safe_query_function(args):
        vals = ', '.join("'%s'" % pymysql.escape_string(v) for v in args['city'])
        return 'SELECT * FROM sales WHERE city IN (%s)' % vals

**Never use args outside quotes**, e.g. when referring to column names. Ensure
that the column names are always specified by you. For example:

    :::python
    def bad_query_function(args):
        return 'SELECT {col} FROM table'.format(args['col'][0])

    def good_query_function(args):
        # Ensure that only these 2 columns we specify can be included.
        columns = {'sales': 'sales', 'growth': 'growth'}
        return 'SELECT {col} FROM table'.format(columns[args['col'][0]])

## FormHandler defaults

To specify default values for arguments, use the `default:` key.

    :::yaml
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

## FormHandler prepare

To modify the arguments before executing the query, use `prepare:`.

    :::yaml
    url:
      replace:
        pattern: /$YAMLURL/replace
        handler: FormHandler
        kwargs:
          url: $YAMLPATH/flags.csv
          prepare: args.update(Stripes=args.pop('c', []))
          # Another example:
          # prepare: my_module.calc(args, handler)

This `prepare:` method replaces the `?c=` with `?Cross=`. So
[replace?c=Yes](replace?c=Yes&_format=html) is actually the same as
[flags?Cross=Yes](flags?Cross=Yes&_format=html).

`prepare:` is a Python expression that modifies `args`. `args` is a dict
containing the URL query parameters as lists of strings. `?x=1&y=2` becomes is
`{'x': ['1'], 'y': ['2']}`. `args` has [default values](#formhandler-defaults)
merged in. You can modify `args` in-place and return None, or return a value that
replaces `args`.

Some sample uses:

- Add/modify/delete arguments based on the user. You can access the user ID via
  `handler.current_user` inside the `prepare:` expression
- Add/modify/delete arguments based on external data. 
- Replace argument values. 


## FormHandler multiple datasets

You can return any number of datasets from any number of sources. For example:

    :::yaml
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

## FormHandler templates

The output of FormHandler can be rendered as a custom template using the
`template` format. For example, this creates a ``text`` format:

    :::yaml
    url:
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

    :::yaml
    url:
      flags:
        pattern: /$YAMLURL/flags
        handler: FormHandler
        kwargs:
          url: /path/to/flags.csv
          id: ID                  # Primary key column is "ID"

You may specify multiple primary keys using a list. For example:

    :::yaml
          id: [state, city]     # "state" + "city" is the primary key

If the `id` columns do not exist in the data, or are not passed in the URL,
it raises 400 Bad Request HTTP Error.

A POST, PUT or DELETE operation immediately writes back to the underlying `url`.
For example, this writes back to an Excel file:

    :::yaml
          # Saves data to Sheet1 of file.xlsx with plant & machine id as keys
          url: /path/to/file.xlsx
          sheetname: Sheet1
          id: [plant, machine id]

This writes back to an Oracle Database:

    :::yaml
          # Saves to "sales" table of Oracle DB with month, product & city as keys
          # Typically, the primary keys of "sales" should be the same as `id` here
          url: 'oracle://$USER:$PASS@server/db'           # Reads from Oracle
          table: sales
          id: [month, product, city]

To add or delete multiple values, repeat the keys. For example:

    POST ?id=10&x=1&y=2 & id=11&x=3&y=4   # Inserts {id:10, x:1, y:2} & {id:11, x:3, y:4}
    DELETE ?id=10 & id=11                 # Delete id=10 & id=11

Note: PUT currently works with single values. In the future, it may update
multiple rows based on multiple ID selections.

If you are using [multiple datasets](#formhandler-multiple-datasets), add an
`id:` list to each dataset. For example:

    :::yaml
      excel:
          url: /path/to/file.xlsx
          sheetname: Sheet1
          id: [plant, machine id]
      oracle:
          url: 'oracle://$USER:$PASS@server/db'
          table: sales
          id: [month, product, city]

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

    :::html
    <!-- flags.csv has ID, Name, Text and many other fields -->
    <form action="flags-add" method="POST" enctype="multipart/form-data">
      <label for="ID">ID</label>     <input type="text" name="ID" value="XXX">
      <label for="Name">Name</label> <input type="text" name="Name" value="New country">
      <label for="Text">Text</label> <input type="text" name="Text" value="New text">
      <input type="hidden" name="_xsrf" value="{{ handler.xsrf_token }}">
      <button type="submit" class="btn btn-submit">Submit</button>
    </form>

We need to specify a primary key. This YAML config specifies `ID` as the primary key.

    :::yaml
          id: ID        # Make ID the primary key

When the HTML `form` is submitted, field names map to column names in the data.
For example, `ID`, `Name` and `Text` are columns in the flags table.

You can insert multiple rows. The number of rows inserted is returned in the
`Count-<dataset>` header.

The form can also be submitted via AJAX. See [FormHandler PUT](#formhandler-put)
for an AJAX example.

### FormHandler PUT

This PUT request updates an existing row in the data.

    :::js
    // flags.csv has ID, Name, Text and many other fields
    $.ajax('flags-edit', {
      method: 'PUT',
      headers: xsrf_token,      // See documentation on XSRF tokens
      data: {ID: 'XXX', Name: 'Country 1', Text: 'Text ' + Math.random()}
    })

We need to specify a primary key. This YAML config specifies `ID` as the primary key.

    :::yaml
          id: ID        # Make ID the primary key

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

    :::html
    <!-- flags.csv has Name as a column -->
    <form action="flags-delete" method="POST" enctype="multipart/form-data">
      <input type="hidden" name="x-http-method-override" value="DELETE">
      <label for="Name">Name</label> <input type="checkbox" name="Name" value="Country 1" checked>
      <label for="Name">Name</label> <input type="checkbox" name="Name" value="Country 2">
      <button type="submit" class="btn btn-submit">Submit</button>
    </form>

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
