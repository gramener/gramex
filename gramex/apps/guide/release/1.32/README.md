---
title: Gramex 1.32 Release Notes
prefix: 1.32
...

[TOC]

## Logviewer configuration

[Log viewer](../../logviewer/) is now configurable. When importing logviewer,
you can:

- configure the dashboard layout
- add additional panels
- schedule the log viewer as required

## Gramex init

`gramex init` now adds a [.stylelintrc](https://stylelint.io/user-guide/configuration/)
file that checks for CSS issues. The [.htmllintrc](https://github.com/htmllint/htmllint/wiki/Options)
file is also improved

## Tornado 5.0

Gramex now supports [Tornado 5.0](https://tornado.readthedocs.io/en/stable/releases/v5.0.0.html)
on Python 3. Tornado 5.0 uses the native
[asyncio](https://docs.python.org/3/library/asyncio.html) library. This meant
re-writing some of Gramex's internals.

There are still a few kinks to sort out, though.

## YAML merge variables

`gramex.yaml` supports an `import.merge:` key that copy-pastes a configuration
in-place. This is mainly used when writing re-usable Gramex applications /
services. See [merging variables](../../config/#merging-variables).

## CaptureHandler Proxy

[CaptureHandler with Chrome](../../capturehandler/#chrome) respects proxy
environment variables. If your proxy IP is `10.20.30.40` on port `8000`, then set
`ALL_PROXY`, `HTTPS_PROXY` or `HTTP_PROXY` to `10.20.30.40:8000`.

## Internal bugfixes

Gramex internals have a few important bug fixes.

- Changing the Gramex configuration used to re-initialize configurations even
  if they hadn't changed. This is resolved.
- If multiple instances of Gramex are running, this caused shared `sqlite`
  sessions to report errors on already purged keys. This is resolved.

## Stats

- Code base: 23,896 lines (python: 14,928, javascript: 1,231, tests: 8,074)
- Test coverage: 79%

## Upgrade

To upgrade Gramex, run:

```bash
pip install --verbose gramex==1.32
```

This downloads Chromium and other front-end dependencies. That may take time.
