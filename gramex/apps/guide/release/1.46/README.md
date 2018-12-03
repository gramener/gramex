---
title: Gramex 1.46 Release Notes
prefix: 1.46
...

[TOC]

## Vega gallery

Chord diagrams, Circle packs, Boxplots, Radial charts, Sunburst, Donut charts and
few more examples are added to [chart gallery](../../chart/gallery.html)

[![vega-g](../1.44/vega-gallery.png)](../../chart/gallery.html)

(Contributions from:
[@vikky.a](https://code.gramener.com/vikky.a),
[@lakshmi.s](https://code.gramener.com/lakshmi.s)
)

More examples & utilities will be added, watch out this space for more updates.

[See the chart gallery](../../chart/gallery.html).

## ModelHandler

[ModelHandler](../../modelhandler/) exposes machine learning models as APIs
that applications can use via Python or over a REST API.

To do so, add a `modelhandler` endpoint

```yaml
url:
  modelhandler:
    pattern: /$YAMLURL/model/(.*?)/(.*?)
    handler: ModelHandler
    kwargs:
      path: $YAMLPATH  # The local directory to store model files/training data etc.
```

You could submit URL query parameters like `FormHandler`
`/model/<name>/?col1=val1&col2=val2&col1=val3..
to train a dataset, classify a record, inserts data, delete model etc.

This will help you create quick forms like below

[![mlform](https://code.gramener.com/cto/gramex/uploads/b23321441915dadd54e615f12f34f7d8/image.png)](../../modelhandler/#example-usage)

[See the documentation](../../modelhandler/).

## Admin

### Admin info

The info page shows information about versions, paths and other details about
Gramex and its dependencies.

To enable it, ensure that you specify:

- Either `components: [..., info, ...]`, i.e. include `info` in `components:`
- Or do not specify any `components:`

This exposes JSON data at `<admin-page>/info` as a list of objects consistent
with [FormHandler](../../formhandler/).

```json
[
    {"section":"git","key":"path","value":"D:\\bin\\git.EXE","error":null},
    {"section":"git","key":"version","value":"git version 2.15.1\n","error":""},{"section":"gramex","key":"memory usage","value":153411584,"error":""},
    ...
]
```

[See the documentation](../../admin/#admin-info).

[See the Admin info](../../admin/admin-kwargs/?tab=info).

### Admin console (webshell)

Webshell now makes `handler` object avaiable to the user.
This will make `handler` related debugging easier.

[![vega-g](../1.41/python-admin-console.gif)](../../admin/admin-kwargs/?tab=shell)


## Developer Updates

### bootstrap.bundle.js

[`gramex init`](../../init/) uses `bootstrap.bundle.js` in  instead of adding `popper.js`

You can use

```html
<script src="ui/jquery/dist/jquery.min.js"></script>
<script src="ui/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
```

## Other Updates

### gramex init

We've added an asciinema for [`gramex init`](../../init/)

<link rel="stylesheet" type="text/css" href="../../node_modules/asciinema-player/resources/public/css/asciinema-player.css">
<asciinema-player src="../../init/gramex-init.rec" cols="100" rows="25" idle-time-limit="0.5"></asciinema-player>
<script src="../../node_modules/asciinema-player/resources/public/js/asciinema-player.js"></script>

## Stats

- Code base: 28,993 lines (python: 17,411, javascript: 1,852, tests: 9,730)
- Test coverage: 78%

## Upgrade

Note: `gramex >= 1.41` onwards requires `Anaconda >= 5.2.0`

To upgrade Gramex, run:

```bash
pip install --verbose gramex==1.46
```

To upgrade apps dependencies, run:

```bash
gramex setup --all
```

This downloads Chromium and other front-end dependencies. That may take time.
