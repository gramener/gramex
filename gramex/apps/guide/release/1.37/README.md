---
title: Gramex 1.37 Release Notes
prefix: 1.37
...

[TOC]

## R interface

[R](http://www.r-project.org/) is a scripting language popular for data analysis, statistics,
and graphics. Gramex now provides an interface for users to run [R commands](../../r/#r-commands)
and [R scripts](../../r/#r-scripts) and allows you take advantage of R functions,
libraries, packages, and even saved models.

```python
import gramex.ml
total = gramex.ml.r('sum(c(1,2,3))')    # Add up numbers and return the result

gramex.ml.r(path='sieve.R')             # Loads relative to the Python file
```

Gramex also converts Pandas, Numpy objects automatically into R vectors, and vice versa.

![ggplot](../../r/plot_async.png)

[See the documentation](../../r/).

## CaptureHandler tutorial

Gramex now has a [CaptureHandler tutorial](../../tutorials/capturehandler.md/) that explains how to
setup CaptureHandler, Schedule a CaptureHandler service and lists down supported arguments

## Apache reverse proxy

Apart from documenting how to setup minimal
[nginx reverse proxy](../../deploy/#nginx-reverse-proxy) for Gramex apps,
Gramex guide also documents how to setup [Apache reverse proxy](../../deploy/#apache-reverse-proxy).

## Developer Updates

- The Google Font [Montserrat](https://fonts.google.com/specimen/Montserrat) 
is now available on the Gramex [UI components](../../uicomponents/).

- [Goaccess](https://goaccess.io/) is useful for server monitoring based on logs. 
Nearly all web log formats (Apache, Nginx, Amazon S3, CloudFront, etc) are supported.
Simply set the log format and run it against your log.
[Read deploy](../../deploy/#nginx-log-analyzer) notes to set it up for Gramex Apps.

## Bug fixes

- FormHandler vega charts used to overwrite kwargs, therby failing on second loads.
This is now fixed.
[#415](https://code.gramener.com/cto/gramex/issues/415)

- DBAuth used to allow user to login by making POST request with empty username
or/and password. This is now plugged.
[#399](https://code.gramener.com/cto/gramex/issues/399)
[#413](https://code.gramener.com/cto/gramex/issues/413)

## Stats

- Code base: 25,909 lines (python: 15,736, javascript: 1,518, tests: 8,655)
- Test coverage: 79%

## Upgrade

To upgrade Gramex, run:

```bash
pip install --verbose gramex==1.37
```

This downloads Chromium and other front-end dependencies. That may take time.
