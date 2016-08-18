title: Gramex runs SQL queries

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

    url:
        flags:
            pattern: /$YAMLURL/flags                # The flags URL...
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

You can also specify the default `limit:` (number of rows) in the response as
well as the `format:` (which can be `html`, `csv`, `xlsx` or `json` -- see
[DataHandler formats](../datahandler/#datahandler-formats).)

URL query parameters can override these. For example:

- [flags?content=Europe](flags?content=Europe) shows flags for Europe
- [flags?format=json](flags?format=json) renders the flags in JSON
- [flags?limit=20](flags?limit=20) shows 20 rows instead of the default 10

The `query:` section freezes these values, and they cannot be overridden by the
URL query parameters. For example:

- [flags?c1=0](flags?c1=0) will not set `c1` to 0 -- the `query:` section has
  frozen this value at 10.
