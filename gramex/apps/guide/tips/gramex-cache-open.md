---
title:  Cache and open files
prefix: Tip
...

The feature I use most often in Gramex 0.18 is `gramex.cache.open`. It's a simple replacement for reading CSV, XSLX files, etc. But it also caches.

For those familiar with Gramex 0.x, it's exactly like `DB.csv` or `DB.open`.

In fact, don't ever use the regular `open`, `io.open` or `pd.read_csv`. Always use gramex.cache.open. It's vastly better.

**Read files**

To read a CSV file, use just:

    :::py
	data = gramex.cache.open('data.csv', 'csv')

You can call this as often as you like. The DataFrame will be re-loaded only if the file is updated.

You can pass additional parameters to `read_csv`, like:

    :::py
	data = gramex.cache.open('data.csv', 'csv', encoding='utf-8')

**File formats**

The second parameter can be any of `text`, `json`, `yaml`, `xlsx`, etc. You can pass additional parameters to all of these. `json` and `yaml` use `json.load` and `yaml.load`. The rest use `pandas.read_*`

You can also use "markdown" as the second parameter. That converts Markdown to a HTML string.

**Custom calculations**

The second parameter can be any function that takes a filename (and any optional parameters) to return anything. You can put in calculations in here to return any value.

For example:

    :::py
	def compute(filename):
	    data = pd.read_csv(filename)
	    return {
	        'columns': data.columns,
	        'summary': data.groupby('category')['sales'].sum()
	    }

    :::py
	data = gramex.cache.open('data.csv', compute)

The first time, the result is the same as compute('data.csv'). After that, the result is cached. When data.csv is changed, compute is called again.

**Global cache**

The data is cached globally across the Gramex instance. You can reload this from across different functions or modules. The cache still remains.

Always use it

Like I mentioned: there's no reason NOT to use `gramex.cache.open`. Replace all file open methods with this.
