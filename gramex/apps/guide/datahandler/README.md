title: Gramex connects to data

`DataHandler` let's you fetch data from CSV files and databases, and returns the result as CSV, JSON or HTML tables. Here is a sample configuration that browses [gorilla genes](genome?format=html&limit=10):

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

To start you off, there's a `database.sqlite3` in this application folder. (Gramex downloaded [flags data](https://gramener.com/flags/) on startup. See [fetch.data()](fetch.py) and the scheduler in [gramex.yaml](gramex.yaml).

The `DataHandler` below exposes the flags table in `database.sqlite3` at the URL [flags](flags).

    :::yaml
    flags:
      pattern: /$YAMLURL/flags                # The URL /datastore/flags
      handler: DataHandler                    # uses DataHandler
      kwargs:
          driver: blaze                               # with blaze or sqlalchemy driver
          url: sqlite:///$YAMLPATH/database.sqlite3   # to connect database at this path/url
          table: flags                                # on this table
          parameters: {encoding: utf8}                # with additional parameters provided
          thread: false                               # Disable threading if you see weird bugs
          default:
              format: html                            # Can also be json or csv

Once we have this setup, we can query the data with a combination of parameters like `select`, `where`, `groupby`, `agg`, `offset`, `limit`, `sort`

- `select` retrieves specific columns. E.g. [?select=Name&select=Continent](flags?select=Name&select=Continent)
- `where` filters the data. E.g. [?where=Stripes=Vertical](flags?where=Stripes==Vertical). You can use the operators `=` `&gt;=` `&lt;=` `&gt;` `&lt;` `!=`. Multiple conditions can be applied. E.g. [where=Continent=Asia&where=c1>50](flags?where=Continent=Asia&where=c1>50)
- `group` to group records on columns and aggregate them. E.g. [?groupby=Continent&agg=c1:sum(c1)](flags?groupby=Continent&agg=c1:sum(c1))
- `agg` - return a single value on grouped collection. Supported aggregations include `min`, `max`, `sum`, `count`, `mean` and `nunique`. E.g. [groupby=Continent&agg=nshapes:nunique(Shapes)](flags?groupby=Continent&agg=nshapes:nunique(Shapes))
- `limit` - limits the result to n number of records. By default, the first 100 rows are displayed. E.g. [?limit=5](flags?limit=5) shows the first 5 rows.
- `offset` - excludes the first n number of records. E.g. [?offset=5&limit=5](flags?offset=5&limit=5) shows the next 5 rows
- `sort` - sorts the records on a column in ascending order by default. You can change the order with the `:asc` / `:desc` suffixes. E.g. [?sort=Symbols:desc](flags?sort=Symbols:desc)
- `format` - determines the output format. Can be `html`, `json`, `csv`. E.g. [?format=json](flags?format=json)

Examples:

- [?groupby=Continent&agg=count:nunique(Name)&agg=shapes:count(Shapes)&sort=count:desc](flags?groupby=Continent&agg=count:nunique(Name)&agg=shapes:count(Shapes)&sort=count:desc): For every Continent, show the number of unique countries and the numbrr of countries with shapes

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

**A note on threading**. By default, DataHandler runs the query in a separate
thread. However, this code is not currently stable. If you find tables that seem
to be missing columns, or errors that are not reproducible, use `thread: false`
to disable threading (as of v1.13.) Upcoming versions will fix threading issues.


## DataHandler defaults

These parameters can be specified specified in the URL. But you can also set these as defaults. For example, adding this section under `kwargs:` ensures that the default format is HTML and the default limit is 10 -- but the URL can override it.

    :::yaml
    default:
        format: html
        limit: 10

You can make the parameters non-over-ridable using `query:` instead of `default:`. For example, this section forces the format to html, irrespective of what the `?format=` value is. However, `?limit=` will override the default of 10.

    :::yaml
    query:
        format: html
    default:
        limit: 10

## Database edits

You can use the `POST`, `PUT` and `DELETE` methods to add, update or delete rows in a database using DataHandler. You need to use [XSRF cookies](../filehandler/#xsrf) when using these methods.

(The examples below use [jQuery.ajax][jquery-ajax] and the [cookie.js][cookie.js] libraries.)

[jquery-ajax]: http://api.jquery.com/jquery.ajax/
[cookie.js]: https://github.com/florian/cookie.js

<script src="https://cdnjs.cloudflare.com/ajax/libs/cookie.js/1.2.0/cookie.min.js"></script>

### DataHandler insert

`POST` creates a new row. You can specify the `val` parameter with one or module `column=value` expressions. For example, this inserts a row with the `Name` column as `United Asian Kingdom` and `ID` of `UAK`:

    :::js
    var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
    $.ajax('flags', {
      headers: xsrf,
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

`PUT` updates existing rows. The `where` parameter selects the rows to be updated. The `val` parameter defines the values to be updated. For example, this updates all rows where the `ID` is `UAK` and sets the `Content` and `Text` columns:

    :::js
    $.ajax('flags', {
      headers: xsrf,
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
      headers: xsrf,
      method: 'GET',
      data: {where: 'ID=UAK', format: 'json'}
    })
    // OUTPUT

### DataHandler delete

`DELETE` deletes existing rows. The `where` parameter selects the rows to be deleted. For example, this deletes all rows where the `ID` is `UAK`:

    :::js
    $.ajax('flags', {
      headers: xsrf,
      method: 'DELETE',               // Delete all rows
      data: {
        where: 'ID=UAK',              // where the ID column is UAK
        where: 'Continent=Asia'       // AND the Content column is Asia
      }
    })

<script>
var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
var pre = [].slice.call(document.querySelectorAll('pre'))

function next() {
  var element = pre.shift()
  var text = element.textContent
  if (text.match(/\$.ajax/)) {
    eval(text)
      .always(function(result) {
        element.innerHTML = element.innerHTML.replace(/OUTPUT/, 'OUTPUT<br>' + JSON.stringify(result))
        if (pre.length > 0) next()
      })
  }
  else if (pre.length > 0) next()
}
next()
</script>
