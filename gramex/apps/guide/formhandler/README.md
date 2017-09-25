title: Gramex connects to data

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

## FormHandler filters

The URL supports operators for filtering rows. The operators can be combined.

- [?Continent=Europe](flags?Continent=Europe&_format=html) ► Continent = Europe
- [?Continent=Europe&Continent=Asia](flags?Continent=Europe&Continent=Asia&_format=html)
  ► Continent = Europe OR Asia. Multiple values are allowed
- [?Continent!=Europe](flags?Continent!=Europe&_format=html) ► Continent is NOT Europe
- [?Continent!=Europe&Continent!=Asia](flags?Continent!=Europe&Continent!=Asia&_format=html)
  ► Continent is NEITHER Europe NOR Asia
- [?c1>=10](flags?c1>=10&_format=html) ► c1 > 10 (not >= 10)
- [?c1>~=10](flags?c1>~=10&_format=html) ► c1 >= 10. The `~` acts like an `=`
- [?c1<=10](flags?c1<=10&_format=html) ► c1 < 10 (not <= 10)
- [?c1<~=10](flags?c1<~=10&_format=html) ► c1 <= 10. The `~` acts like an `=`
- [?c1>=10&c1<=20](flags?c1>=10&c1<=20&_format=html) ► c1 > 10 AND c1 < 20
- [?Name~=United](flags?Name~=United&_format=html) ► Name matches &_format=html
- [?Name!~=United](flags?Name!~=United&_format=html) ► Name does NOT match United
- [?Name~=United&Continent=Asia](flags?Name~=United&Continent=Asia&_format=html) ► Name matches United AND Continent is Asia

To control the output, you can use these control arguments:

- [?_limit=10](flags?_limit=10&_format=html) ► show only 10 rows
- [?_offset=10&_limit=10](flags?_offset=10&_limit=10&_format=html) ► show only 10 rows starting, skipping the first 10 rows
- [?_sort=Continent&_sort=Name](flags?_sort=Continent&_sort=Name&_format=html) ► sort first by Continent (ascending) then Name (ascending)
- [?_sort=-Continent&_sort=-ID](flags?_sort=-Continent&_sort=-ID&_format=html) ► sort first by Continent (descending) then ID (descending)
- [?_c=Continent&_c=Name](flags?_c=Continent&_c=Name&_format=html) ► show only the Continent and Names columns
- [?_c=-Continent&_c=-Name](flags?_c=-Continent&_c=-Name&_format=html) ► show all columns except the Continent and Names columns

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

The query string is string-formatted using the arguments. For example:

    :::yaml
          query: 'SELECT {group}, COUNT(*) FROM table GROUP BY {group}'

will group by whatever is passed as `?group=`. For example, `?group=city` returns
`SELECT city, COUNT(*) FROM table GROUP BY city`.

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
          # modify: my_module.calc(args, handler)

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
