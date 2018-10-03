---
title: Gramex 1.43 Release Notes
prefix: 1.43
...

[TOC]


## FormHandler Edits Modify

[FormHandler Edit](.././formhandler/#formhandler-edits) methods now supports `modify:` method.  For PUT, POST, etc, methods now you can run an action AFTER the edit action.

Below configuration has two `modify:` -- which are called after edit operation.

```yaml
  formhandler-edits-multidata-modify:
    pattern: /$YAMLURL/edits-multidata-modify
    handler: FormHandler
    kwargs:
      csv:
        url: $YAMLPATH/sales-edits.csv
        encoding: utf-8
        id: [city, product]
        modify: emailer.send
      sql:
        url: mysql+pymysql://root@$MYSQL_SERVER/DB?charset=utf8
        table: sales
        id: [city, product]
      modify: emailer.sendall
```

`modify:` can be any expression/function that uses `data` -- count of records edited and `handler` -- `handler.args` contains data submitted by the user.

## Developer Updates

- For Chrome [CaptureHandler](../../capturehandler/#chrome) -- you can now specify
  - `width=`: viewport width in pixels. (Default: 1200px). Only for Chrome
  - `height=`: viewport height in pixels. (Default: 768px). Only for Chrome
  - `media=`: `print` or `screen`. Defaults to `screen`. Only for Chrome

This also fixes responsive layouts in PDF and PNG downloads.

- Chrome [CaptureHandler](../../capturehandler/#chrome) which depends on puppeteer is now upgraded to version `^1.8.0`.
This fixes [#505](https://code.gramener.com/cto/gramex/issues/505)

## Bug fixes

- Admin app earlier was failing when imported under a namespace. This is now fixed.
[#500](https://code.gramener.com/cto/gramex/issues/500)
- Multiple namespace imports were not currenlt prefixed.
Supportting lists in import path (with namespace) was needed. This is now plugged.
[#502](https://code.gramener.com/cto/gramex/issues/502)

## Stats

- Code base: 28,057 lines (python: 16,890, javascript: 1,793, tests: 9,374)
- Test coverage: 79%

## Upgrade

Note: `gramex >= 1.41` onwards requires `Anaconda >= 5.2.0`

To upgrade Gramex, run:

```bash
pip install --verbose gramex==1.43
```

To upgrade apps dependencies, run:

```bash
gramex setup --all
```

This downloads Chromium and other front-end dependencies. That may take time.
