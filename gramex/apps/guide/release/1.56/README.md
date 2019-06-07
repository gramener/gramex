---
title: Gramex 1.56 release notes
prefix: 1.56
...

[TOC]

## Vega parameter substitution

Vega charts now support [parameter substitution](../../formhandler/#parameter-substitution)

For example, with below configuration you can control `CHART_TYPE`, `COL_DIMENSION`, 
`COL_METRIC` from URL args `?_format=barchart&CHART_TYPE=bar&COL_METRIC=c4`

```yaml
url:
  ....
      formats:
        barchart:
          spec:
            ...
            mark: '{CHART_TYPE}'
            encoding:
              x: {field: '{COL_DIMENSION}', type: ordinal}     # COL_DIMENSION set to dim for ?COL_METRIC=dim
              y: {field: '{COL_METRIC}', type: quantitative}   # COL_METRIC set to val for ?COL_METRIC=val
```

## URL Driven Dashboards Tutorial

Guide tutorials are restructed and updated to effectively guide you to build URL Driven Dashboards.

List of current tutorials:

- [Tutorials](../../tutorials/)
    - [Quickstart](../../tutorials/quickstart/)
    - [Dashboards](../../tutorials/dashboards/)
    - [Charts](../../tutorials/charts/)
    - [Dropdown & Search](../../tutorials/g1-dropdown)

## Chrome device emulation

[Chrome capture](../../capturehandler) now supports device emulation. 

For example, `?emulate=iPhone 6&...` uses `iPhone 6` userAgent for device emulation.
This is useful for external websites where content is served based on device userAgent.

Puppeteer version is upgraded to `1.17.0`

## UI component upgrades

g1 is upgraded from 0.17.0 to 0.17.1, which introduces

- [$().template()](../../g1/template) exposes variables `$node` (the source node) and `$data` (its `data-` attributes)
- [$.urlchange](../../g1/urlchange) emits a `#?` event when any URL query key
changes. This is in addition to the `#?<key>` and `#` events.

- UI components now include support responsive font sizes.
You can enable with `?enable-responsive-font-sizes=true` (default: false)

Other UI components have also been updated to the latest patch versions.

## Other enhancements

- [pptxhandler](../../pptxhandler) now supports styling specific table columns, all other take default style.
And, in grouped charts, dataframe column order is preserved.
Via [@nivedita.deshmukh](https://code.gramener.com/nivedita.deshmukh)

## Bug fixes

- [admin/schedule](../../admin/admin/schedule) should not succeed if server fails with no response

## Statistics

The Gramex code base has:

- 18,663 lines of Python
- 4,010 lines JavaScript
- 10,491 lines of test code
- 80% test coverage

## How to upgrade

To upgrade Gramex, run:

```bash
pip install --upgrade gramex
pip install --upgrade gramexenterprise    # If you use DBAuth, LDAPAuth, etc.
gramex setup --all
```
