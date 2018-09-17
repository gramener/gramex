---
title: Gramex 1.42 Release Notes
prefix: 1.42
...

[TOC]


## Admin Module

From v1.42, Gramex ships with an admin page. To include it in your page, use:

```yaml
import:
  admin/admin:
    path: $GRAMEXAPPS/admin2/gramex.yaml    # Note the "admin2" instead of "admin"
    YAMLURL: /$YAMLURL/admin/               # URL to show the admin page at
```

Note the `admin2` instead of `admin`

You can configure the admin page as follows:

```yaml
import:
  admin/admin-kwargs:
    path: $GRAMEXAPPS/admin2/gramex.yaml
    YAMLURL: /$YAMLURL/admin-kwargs/        # URL to show the admin page at
    ADMIN_KWARGS:
      logo: https://gramener.com/uistatic/gramener.png      # Logo URL
      title: Admin  Page Options                            # Navbar title
      components: [info, users, shell]                      # Components to show
      theme: '?primary=%2320186f&dark=%2320186f&font-family-base=roboto&body-bg=%23f8f8f8'  # Bootstrap theme query
```

The `ADMIN_KWARGS` section accepts the following parameters:

- `logo`: Logo image URL. Either an absolute URL or relative to the admin page.
- `title`: Title displayed on the navbar. Defaults to "Admin"
- `theme`: The UI theme for the page. For example,
  `?font-family-base=Roboto` makes the font Roboto.
- `components`: List of components to display. The admin page has pre-defined
  components (documented below). By default, all components are displayed.

[Read the documentation](../../admin/) on how to set it up admin page.

## Offline Docker Install

You can now install gramex with [Offline Docker Install](../../install/#offline-docker-install).
This allows you to ship gramex applications to machines that aren't always connected to internet.

## Webshell

[`webshell`](../../admin/admin-kwargs/?tab=shell) now supports arrow keys to navigate history.

![Python Console](../1.41/python-admin-console.gif)

[Read the documentation](../../admin/) on how to set it up admin page.

## Developer Updates

- `YAML` merge with duplicate keys, are now reported with detailed key path.
- When `FormHandler` GET fails for unknown reason, we now report internal server error.

## Bug fixes

- In some versions of Python, the dict order is not defined. 
`WebSocketHandler` constructs methods dynamically and needs method order. This is now fixed.
- When multiple requests are sent to CaptureHandler simultaneously. Downloads get mixed up.
This is now plugged. [#494](https://code.gramener.com/cto/gramex/issues/494)
- If a `schedule` is changed, all schedules are stopped. Changed schedules are re-created.
Unchanged schedules should be scheduled again. This is noe fixed.

## Stats

- Code base: 28,005 lines (python: 16,877, javascript: 1,793, tests: 9,335)
- Test coverage: 79%

## Upgrade

Note: `gramex >= 1.41` onwards requires `Anaconda >= 5.2.0`

To upgrade Gramex, run:

```bash
pip install --verbose gramex==1.42
```

To upgrade apps dependencies, run:

```bash
gramex setup --all
```

This downloads Chromium and other front-end dependencies. That may take time.
