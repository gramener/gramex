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
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/logviewer/gramex.yaml">Source</a>
</div>

## Logviewer usage

Use `LOGVIEWER_*` variables to configure your app.

- `LOGVIEWER_PATH_UI`: path to customized layout config. Use sample default `$GRAMEXAPPS/logviewer/config.yaml` layout
- `LOGVIEWER_PATH_RENDER`: path to customized renderer config. Use sample default `$GRAMEXAPPS/logviewer/render.js` js file
- `LOGVIEWER_FORMHANDLER_KWARGS`: to update `url.name.kwargs` section
- `LOGVIEWER_FORMHANDLER_QUERIES`: to update or add to `queries` section  of `/$YAMLURL/query/` formhandler
- `LOGVIEWER_CAPTURE_KWARGS`: to pass additional kwargs to capture handler
- `LOGVIEWER_SCHEDULER_PORT`: when running multiple instances of gramex, you can control to run scheduler only once from certain port
- `LOGVIEWER_SCHEDULER_SETUP`: to control frequency when to run the scheduler. Default: daily.
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
    LOGVIEWER_LAYOUT_KWARGS:
      auth:                                  # Add auth to layout page
        login_url: /$YAMLURL/login
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
    LOGVIEWER_SCHEDULER_PORT: '9006'  # run scheduler only on --listen.port=9006
    LOGVIEWER_PATH_UI: $YAMLPATH/logviewer-config.yaml    # local .yaml file
    LOGVIEWER_PATH_RENDER: $YAMLPATH/logviewer-render.js  # local js file
    LOGVIEWER_CAPTURE_KWARGS:
      timeout: 30              # Change timeout to 30
    LOGVIEWER_SCHEDULER_SETUP:
      minutes: 45              # Change minute to 45
    LOGVIEWER_SCHEDULER_KWARGS:
      transforms: # Add custom transforms, default transforms will be replaced
      - type: derive
        expr:
          col: user.id
          op: NOTIN
          value: ['-', 'dev']
        as: user.id_1
```

## logviewer.db

Gramex logs all HTTP requests to `logs/requests.csv` under `$GRAMEXDATA`.

It logs:

- `time`: Time of the request in milliseconds since epoch
- `ip`: The IP address of the client requesting the page
- `user.id`: The unique ID of the user requesting the page
- `status`: The HTTP status code of the response (e.g. 200, 500)
- `duration`: Time taken to serve the request in milliseconds
- `method`: The HTTP method requested (e.g. GET or POST)
- `uri`: The full URL requested (after the host name)
- `error`: Any error raised while processing the request

Typical `requests.csv` looks like

```js
1530008663609.0,::1,,200,2708.0,GET,/,
1530008665319.0,::1,,200,948.0,GET,/ui/jquery/dist/jquery.min.js,
1530008665404.0,::1,,200,81.0,GET,/script.js,
1530008665410.0,::1,,200,1.0,GET,/style.css,
1530008667319.0,::1,,404,678.0,GET,/favicon.ico,HTTPError: HTTP 404: Not Found
1530012727106.0,::1,user1,200,210.0,GET,/,
1530012729481.0,::1,,200,74.0,GET,/ui/jquery/dist/jquery.min.js,
1530012729538.0,::1,user2,200,1.0,GET,/script.js,
1530012729594.0,::1,,200,2.0,GET,/style.css,
```

By default, `requests.csv` are backed up on a weekly basis with date prefix.
For eg: `requests.csv.2017-11-21`.

Logviewer application uses data from `logviewer.db` for the front-end visuals.
`logviewer.db` stores the aggregated data (day (aggD), week (aggW), month (aggM)) tables of `requests.csv*`.

Data is grouped for every combination of (`time` (daily), `user.id`, `ip`, `status`, `uri`) and
aggregrated on (`duration`, `new_session`, `session_time`) metrics with (`_count`, `_sum`) suffix.

- `duration_count` - Count of requests for given row combination
- `duration_sum` - Sum of the requests's time taken to serve the request in ms

### Session Calculations

Every time a user logs into a gramex app, a `new_session` is flagged.
`session_time` duration (in seconds) is the length of time someone spends on the app.

For example, let's take `user1`

- `user1` logs in at `10:00AM` on page `/page1`
- Does nothing for next few minutes
- Hits `/page2` at `10:05AM` -- right now `user1`'s session_time is `5mint `and counting.
- By default, a `15mint` threshold is considered to flag `new_session`.
- Now the `user1` comes back again at `11:30AM`
- This request is flagged for `new_session` and `session_time` is reset for this session.

Let's take another scenario:

- `user2` hits `/page1` at `02:00PM`
- `user2` hits `/page2` at `02:10PM`
- `user2` hits `/page3` at `02:18PM`
- Total sessions by `user2` is `1` and `session_time` is `18mint`

Session related metrics include:

- `new_session_sum` - Total number of sessions
- `session_time_sum` - Total time spent by the user on given `uri` `user.id` `ip` `time:freq` combination

Note: You'd want to ignore test users, non-logged-in users [`-`, `dev`] for session related calulations.
As they tend to skew the session duration.

Currently, logviewer application having `session` related visuals, is based on following

- [`kpi-avgtimespent`](https://github.com/gramener/gramex/blob/master/gramex/apps/logviewer/gramex.yaml): performs `SUM(session_time_sum)/SUM(new_session_sum)`
- `kpi-sessions`: performs `SUM(new_session_sum)`

You can customize `kpi-avgtimespent` to consider only logged-in users

```yaml
import:
  logviewer:
    path: $GRAMEXAPPS/logviewer/gramex.yaml
    YAMLURL: $YAMLURL/log/
    LOGVIEWER_FORMHANDLER_QUERIES:
      kpi-avgtimespent:
        SELECT SUM(session_time_sum)/SUM(new_session_sum) AS value
        FROM {table}
        WHERE "user.id_1" == 1 {where}
```

[`user.id_1`](https://github.com/gramener/gramex/blob/master/gramex/apps/logviewer/gramex.yaml) by default ignores `['-', 'dev']` users.

## Add custom visuals

TODO

## Add 3rd-party data

TODO
