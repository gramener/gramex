{{ appname }} JS files
================================================================================

Store JavaScript code common to the entire application here.
Dashboard-specific code may reside in the dashboard folders.

A typical file structure would be:

- `js/common.js`:               has common utilities & interactions used by all pages
- `js/<chart-name>.js`:         each chart is stored in a separate file
- `js/<chart-name>.vega.json`:  store Vega specs as JSON files
- `js/<config-name>.json`:      store config file (if any) here

Do not store data files (e.g. tabular data, network data, TopoJSON/GeoJSON maps)
here. These usually go into `assets/data/` and are not be version controlled.
