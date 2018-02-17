---
title: FormHandler enhancements
prefix: Tip
...

FormHandler has two significant enhancements in Gramex 1.22.

**Refresher:** [FormHandler](../formhandler/) lets you load data, filter it, and return in in different formats. It is asynchronous - so other requests will not be delayed while waiting for the database.

This release adds a [modify: parameter](../formhandler/#formhandler-modify). After the data is returned, you can modify or transform it in any way.

This release lets you create [dynamic queries](../formhandler/#formhandler-query) based on the URL query parameter. `SELECT {by}, COUNT(*) GROUP BY {by}` lets the user specify a `?by=city` to group by `city`.

This release also lets you add [default URL query parameters](../formhandler/#formhandler-defaults) that you can modify using the [prepare: parameter](../formhandler/#formhandler-prepare). This lets you modify the user inputs before running the filter.

With these changes, there should be **NO REASON to use FunctionHandler** to fetch data.
