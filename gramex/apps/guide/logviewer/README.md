---
title: Log viewer
prefix: Log viewer
...

[TOC]

From v1.25, Gramex ships with a log file viewer. This configuration mounts the
app at [log/](log/):

```yaml
import:
  logviewer:
    path: $GRAMEXAPPS/logviewer/gramex.yaml   # Source of the app
    YAMLURL: $YAMLURL/log/                    # Location to mount at
    namespace: [url, schedule]                # Avoid name space conflicts
    auth: ...                                 # Restrict access as required
```

<div class="example">
  <a class="example-demo" href="log/">Log Viewer</a>
  <a class="example-src" href="http://code.gramener.com/s.anand/gramex/tree/master/gramex/apps/guide/logviewer/gramex.yaml">Source</a>
</div>
