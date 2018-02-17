---
title: Use views instead of query in FormHandler
prefix: Tip
...

Though [FormHandler supports SQL queries](../formhandler/#formhandler-queries),
using them often is a bad idea. It pulls the entire query from the database and
renders it.

Instead, you're better of creating a [Database View](https://en.wikipedia.org/wiki/View_(SQL)).
A view runs a query and stores it in a table. It auto-updates. It can be queried.

Now, you can filter parameters from the view instead. This is VERY efficient compared to putting in a query.

For example, this is a bad idea:

    :::yaml
    handler: FormHandler
    kwargs:
        url: mysql://server/db
        table: sales
        query: SELECT city, SUM(sales) FROM table GROUP BY city WHERE state="{state}"

Instead use:

    :::yaml
    handler: FormHandler
    kwargs:
        url: mysql://server/db
        table: sales_by_city

... where `sales_by_city` is a view created using `SELECT state, city, SUM(sales) FROM table GROUP BY state, city`.

This way, `FormHandler` only fetches the relevant data for a selected state.
