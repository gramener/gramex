---
title: Log viewer
prefix: Log viewer
...

[TOC]

From v1.25, Gramex ships with a log file viewer.

To use it, add this to your `gramex.yaml`:

```yaml
import:
  logviewer:
    path: $GRAMEXAPPS/logviewer/gramex.yaml   # Source of the app
    YAMLURL: $YAMLURL/log/                    # Location to mount at
    auth: ...                                 # Restrict access as required
```

This configuration mounts the app at [log/](log/):

<div class="example">
  <a class="example-demo" href="log/">Log Viewer</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/logviewer/gramex.yaml">Source</a>
</div>

## Logviewer usage

Use `LOGVIEWER_*` variables to configure your app.

- `LOGVIEWER_PATH_UI`: path to customized layout config. Use sample default `$GRAMEXAPPS/logviewer/config.yaml` layout
- `LOGVIEWER_PATH_RENDER`: path to customized renderer config. Use sample default `$GRAMEXAPPS/logviewer/render.js` js file
- `LOGVIEWER_FORMHANDLER_KWARGS`: to update `url.name.kwargs` section
- `LOGVIEWER_FORMHANDLER_QUERIES`: to update or add to `queries` section  of `/$YAMLURL/query/` formhandler
- `LOGVIEWER_CAPTURE_KWARGS`: to pass additional kwargs to capture handler
- `LOGVIEWER_SCHEDULER_PORT`: when running multiple instances of gramex, you can control to run scheduler only once from certain port
- `LOGVIEWER_SCHEDULER_SETUP`: to control when to run
- `LOGVIEWER_SCHEDULER_KWARGS`: to change `transforms`

All variables are optional.

## Using Variables

Examples usage with `LOGVIEWER_*` variables

```yaml
import:
  ui:
    path: $GRAMEXAPPS/ui/gramex.yaml
    YAMLURL: $YAMLURL/ui/
  logviewer:
    path: $GRAMEXAPPS/logviewer/gramex.yaml
    YAMLURL: $YAMLURL/log/
    LOGVIEWER_FORMHANDLER_KWARGS:
      headers:
        Cache-Control: public, max-age=3600   # cached for 1 hour
    LOGVIEWER_FORMHANDLER_QUERIES:
      kpi-pageviews:  # overwrites existing query
        SELECT SUM(duration_count) AS value
        FROM {table} {where}
      kpi-custom-metric:  # adds new query
        SELECT AVG(duration_count) AS value
        FROM {table} {where}
    LOGVIEWER_SCHEDULER_PORT: '9006'  # run scheduler on --listen.port=9006
    LOGVIEWER_PATH_UI: $YAMLPATH/logviewer-config.yaml    # local .yaml file
    LOGVIEWER_PATH_RENDER: $YAMLPATH/logviewer-render.js  # local js file
    LOGVIEWER_CAPTURE_KWARGS:
      timeout: 30  # Change timeout to 30
    LOGVIEWER_SCHEDULER_SETUP:
      minutes: 45 # Change minute to 45
    LOGVIEWER_SCHEDULER_KWARGS:
      transforms: # Add custom transforms, default transforms will be replaced
      - type: derive
        expr:
          col: user.id
          op: NOTIN
          value: ['-', 'dev']
        as: user.id_1
```

## Add custom visuals

TODO

## Add 3rd-party data

TODO
