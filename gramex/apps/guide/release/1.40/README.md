---
title: Gramex 1.40 Release Notes
prefix: 1.40
...

[TOC]

## FilterHandler

[FilterHandler](../../filterhandler/) lets you filter columns from files and databases.

Here is a sample configuration to filter data columns from a CSV file:

```yaml
url:
  flags:
    pattern: /$YAMLURL/flags
    handler: FilterHandler
    kwargs:
      url: $YAMLPATH/flags.csv
```

- Simple: [flags?_c=Name](../../filterhandler/flags?_c=Name)
returns all unique values of `Name` column
- Muliple Columns: [flags?_c=Name&_c=Continent](../../filterhandler/flags?_c=Name&_c=Continent)
returns all unique values of `Name` and `continent` columns
- Multiple Columns with filter: [flags?_c=Name&_c=Continent&Name=Andorra](../../filterhandler/flags?_c=Name&_c=Continent&Name=Andorra)
returns all unique values of `Name` without filtering `Name=Andorra` and `Continent` by filtering `Name=Andorra`
- Simple Sort Asc: [flags?_c=Name&_sort=Name](../../filterhandler/flags?_c=Name&_sort=Name)
returns Unique values of `Name` sorted by `Name` column in ascending order
- Simple Sort Desc: [flags?_c=Name&_sort=c8](../../filterhandler/flags?_c=Name&_sort=-c8)
returns Unique values of `Name` sorted by `c8` column in descending order

**Credits** to [@nikhil.kabbin](https://code.gramener.com/nikhil.kabbin) for the contribution.

[See the documentation](../../filterhandler/).

## FormHandler modify

[FormHandler](../../formhandler/#formhandler-modify) now supports applying `modify` on multiple datasets.

If you have [multiple datasets](../../formhandler/#formhandler-multiple-datasets),
`modify:` can modify all of these datasets -- and join them if required.

[This example](../../formhandler/modify-multi?_format=html) has two `modify:` --
the first for a single query, the second applies on both datasets.

```yaml
url:
  formhandler-modify-multi:
    pattern: /$YAMLURL/modify-multi
    handler: FormHandler
    kwargs:
      symbols:
        url: sqlite:///$YAMLPATH/../datahandler/database.sqlite3
        table: flags
        query: 'SELECT Continent, COUNT(DISTINCT Symbols) AS dsymbols FROM flags GROUP BY Continent'
        # Modify ONLY this query. Adds rank column to symbols dataset
        modify: data.assign(rank=data['dsymbols'].rank())
      colors:
        url: $YAMLPATH/flags.csv
        function: data.groupby('Continent').sum().reset_index()
      # Modify BOTH datasets. data is a dict of DataFrames.
      modify: data['colors'].merge(data['symbols'], on='Continent')
```

`modify:` can be any expression that uses `data`, which is a dict of DataFrames
`{'colors': DataFrame(...), 'symbols': DataFrame(...)`. It can return a single
DataFrame or any dict of DataFrames.

[See the documentation](../../formhandler/#formhandler-modify).

## g1 dropdown

Dropdown component that integrates well with [`g1.urlfilter`](https://code.gramener.com/cto/g1#urlfilter)

[`$.dropdown`][g1dropdown] requires `bootstrap-select` library and its dependencies.

**Examples:**

```html
<div class="container1"></div>
<script>
  $('.container1').dropdown({data: ['Red', 'Green', 'Blue'] })
</script>
```
The above code snippet renders a dropdown with 3 options Red, Green, Blue using
[bootstrap-select](https://silviomoreto.github.io/bootstrap-select/examples/) library.

```html
<div class="container2"></div>
<script>
  $('.container2').dropdown({ key: 'colors', data: ['Red', 'Green', 'Blue'] })
</script>
```

`key` enables `urlfilter` for `dropdown`. If `Red` option is selected from dropdown,
URL is appended with `?colors=Red`

By default, the selected dropdown values are appended to URL query string.
To append to the hash instead, use `target: '#'`.

```html
<div class="container3"></div>
<script>
  $('.container3').dropdown(
    { key: 'colors',
      data: ['Red', 'Green', 'Blue'],
      target: '#'
    })
</script>
```

To change URL without reloading the page, use `target: 'pushState'`.

To use `bootstrap-select` options, use `options:`

```html
<div class="container5"></div>
<script>
  $('.container5').dropdown({
    data: ['Red', 'Green', 'Blue'], key: 'colors',
    options: {
      style: 'btn-primary',
      liveSearch: true
    }
  })
</script>
```

### $.dropdown events
- `load` is triggered after dropdown is rendered
- `change` is triggered whenever dropdown value is changed

```html
<div class="container5"></div>
<script>
  $('.container5')
  .on('load', function() {
    // Your code here
  })
  .on('change', function() {
    // Your code here
  })
  .dropdown({
    key: 'colors',
    data: ['Red', 'Green', 'Blue']
  })
</script>

```

**Credits** to [@pragnya.reddy](https://code.gramener.com/pragnya.reddy) for the contribution.

[See the documentation][g1dropdown]

## Password Encryption

[DBAuth](../../auth/#database-auth) now allows you to encrypt the password on
client-side (browser) before submitting the credentials. [@sundeep.mallu](https://code.gramener.com/sundeep.mallu)

## Smart Alerts

[Smart Alerts](../../alerts/) now has a video tutorial.

Following examples are updated:

- How to [send a scheduled email](../../alert/#send-a-scheduled-email)
- How to [Avoid re-sending emails](../../alert/#avoid-re-sending-emails)
- How to [Use templates](../../alert/#use-templates)

## MapViewer

[Mapviewer tutorial](../../mapviewer/) is updated with
[`g1.mapviewer`][g1mapviewer] usage with examples
of controls, colors, click events, tooltip.

Video tutorial on Mapviewer usage is added.

Brief overview of Map tools (Mapshaper, QGIS) is provided in the tutorial.

## Logviewer

[Logviewer](../../logviewer/) now runs in a separate thread in the background by default,
allowing gramex to start faster. Metric calculations and underlying queries are updated.
Logviewer Usage options and example(s) are updated.

## Speech Demo

[Speech recognition](../../speech/) demo now has a speech player (talks insights to you!) using  speech synthesis API. Contributed by [@dhiraj.eadara](https://code.gramener.com/dhiraj.eadara)

## Developer Updates

### g1

[`g1.js`](https://code.gramener.com/cto/g1) is upgraded to `0.9.0`, which comes with

- [$.dropdown][g1dropdown] simplifies creating dropdowns
- [g1.mapviewer][g1mapviewer] supports a zoom handler

## Bug fixes

- `gramex.cache.query` used to cache result every time same query is called with `state=None`,
thereby, leaking memory. This is now plugged. [#444](https://code.gramener.com/cto/gramex/issues/444)
- `gramex init` fails if `git` was not configured. Error reporting is now improved.
[#469](https://code.gramener.com/cto/gramex/issues/469)
- [Dynamic emails from data](../../alert/#dynamic-emails-from-data) documentation is updated.
Fixes [#476](https://code.gramener.com/cto/gramex/issues/476)
- Email service fails on Unicode characters. This is fixed [#481](https://code.gramener.com/cto/gramex/issues/481)

## Stats

- Code base: 27,492 lines (python: 16,570, javascript: 1,658, tests: 9,264)
- Test coverage: 79%

## Upgrade

To upgrade Gramex, run:

```bash
pip install --verbose gramex==1.40
```

To upgrade apps dependencies, run:

```bash
gramex setup --all
```

This downloads Chromium and other front-end dependencies. That may take time.

[g1mapviewer]: https://code.gramener.com/cto/g1#g1-mapviewer
[g1dropdown]: https://code.gramener.com/cto/g1#dropdown