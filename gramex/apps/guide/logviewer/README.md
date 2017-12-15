title: Log viewer

[TOC]

From v1.25, Gramex ships with a log file viewer. This configuration mounts the
app at [log/](log/):

    :::yaml
    import:
      logviewer:
        path: $GRAMEXAPPS/logviewer/gramex.yaml   # Source of the app
        YAMLURL: $YAMLURL/log/                    # Location to mount at

Currently, the [log viewer](log/) is rudimentary. It will evolve with Gramex.
v1.26 will feature a more functional version.
