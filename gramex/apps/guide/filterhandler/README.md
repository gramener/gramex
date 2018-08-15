---
title: FilterHandler
prefix: FilterHandler
...

[TOC]

[FilterHandler][filterhandler] lets you filter columns from files and databases.

Here is a sample configuration to filter data columns from a CSV file:

```yaml
url:
  flags:
    pattern: /$YAMLURL/flags
    handler: FilterHandler
    kwargs:
      url: $YAMLPATH/flags.csv
```

You can read from multiple file formats as well as databases. Please follow
[FormHandler](/formhandler/).

## Examples

- Simple: [flags?_c=Name](flags?_c=Name)
returns all unique values of `Name` column

- Muliple Columns: [flags?_c=Name&_c=Continent](flags?_c=Name&_c=Continent)
returns all unique values of `Name` and `continent` columns

- Multiple Columns with filter: [flags?_c=Name&_c=Continent&Name=Andorra](flags?_c=Name&_c=Continent&Name=Andorra)
returns all unique values of `Name` without filtering `Name=Andorra` and `Continent` by filtering `Name=Andorra`

- Simple Sort Asc: [flags?_c=Name&_sort=Name](flags?_c=Name&_sort=Name) returns Unique values of `Name` sorted by `Name` column in ascending order

- Simple Sort Desc: [flags?_c=Name&_sort=c8](flags?_c=Name&_sort=-c8) returns Unique values of `Name` sorted by `c8` column in descending order

## FilterHandler Formats

By default, FilterHandler renders data as JSON. Use `?_format=` to change that.
To see supported formats please refer [FormHandler Formats](/formhandler/#formhandler-formats)

[filterhandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.FilterHandler
