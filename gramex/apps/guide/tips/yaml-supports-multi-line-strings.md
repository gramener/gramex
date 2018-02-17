---
title: YAML supports multi-line strings
prefix: Tip
...

YAML supports multi-line strings. You can wrap text like this:

    :::yaml
    query: >
        SELECT group, SUM(*) FROM table
        WHERE column > value
        GROUP BY group
        ORDER BY group DESC

This is more readable than:

    :::yaml
    query: SELECT group, SUM(*) FROM table WHERE column > value GROUP BY group ORDER BY group DESC
