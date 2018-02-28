---
title: Filter Data Using URL
prefix: Tip
...

All dashboards should be URL-driven. That is, if you copy-paste the URL into another page, the result should be EXACTLY the same.

To do this, our dashboards use URL query parameters to filter data. For example, '?City=Tokyo' shows data where the "City" column equals "Tokyo".

Doing this is very easy in [Gramex 1.21](https://learn.gramener.com/gramex/gramex.html#gramex.data.filter) using `gramex.data.filter` inside a `FunctionHandler`:

    :::python
    result = gramex.data.filter(data, handler.args)

If the URL is `?City=Tokyo` then result is `data[data['City'] == 'Tokyo']`

The URL filter parameters supported are identical to [FormHandler filters](../formhandler/#formhandler-filters).
It supports equals, not equals, comparison and string matches. It also automatically converts the query parameters to the correct type (`int`, `float`, `bool`, `string`, etc)

You can apply this to databases as well. `gramex.data.filter` runs the query on the database, making it faster.

    :::python
    result = gramex.data.filter('oracle://user:pass@server/db',
                                handler.args, table='sales')

This filters the `sales` table in the `Oracle` database based on the URL query parameters.

You should read the [documentation](https://learn.gramener.com/gramex/gramex.html#gramex.data.filter) - it supports more options like:

- a **meta** parameter that returns which URL parameters were not used for filtering, and other information
- **query** and **transform** parameters that transform the data before filtering
