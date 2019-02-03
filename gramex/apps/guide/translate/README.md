---
title: Translate
prefix: Translate
...

[TOC]

**v1.48**. Gramex supports translation on the fly. To set up a translater, use:

```yaml
url:
  translate:
    pattern: /$YAMLURL/translate
    handler: FunctionHandler
    kwargs:
      function: gramex.ml.translater
      kwargs:
        # Get key from https://cloud.google.com/translate/docs/quickstart
        key: ...
        # See list of languages: https://cloud.google.com/translate/docs/languages
        source: en    # Convert from English. Leave it blank to auto-detect
        target: nl    # Convert to Dutch
        # Cache results in this FormHandler structure
        cache:
          url: sqlite:///$YAMLPATH/translate.db
          table: translate
          # Or save in an Excel sheet
          # url: $YAMLPATH/translate.xlsx
```

To translate content in a page, use
[g1 $.translate](https://code.gramener.com/cto/g1/tree/master/docs/translate.md):

```html
<ul>
  <li lang-target="de">This is translated into <em>German</em></li>
  <li lang-target="nl">This is translated into <em>Dutch</em></li>
</ul>
<script src="ui/jquery/dist/jquery.min.js"></script>
<script src="ui/dist/g1/g1.min.js"></script>
<script>
  // Translate text nodes under element with lang-target=
  $('[lang-target]').translate({
    url: './translate',         // Gramex translate URL endpoint
  })
</script>
```

Here is the output (rendered below in real-time using the API):

<ul>
  <li lang-target="de">This is translated into <em>German</em></li>
  <li lang-target="nl">This is translated into <em>Dutch</em></li>
</ul>
<script src="../ui/g1/dist/g1.min.js"></script>
<script>$('[lang-target]').translate({url: 'translate'})</script>

You add `lang-target=` to any number of nodes. All child text nodes are also
translated.

## Translate API

This sets up a URL [translate](translate) that translates using the
[Google Translate API](https://cloud.google.com/translate/).

It accepts the following URL query parameters:

- `?q=` is the string (or list of strings) to be translated.
    - [translate?q=Apple](translate?q=Apple) returns "appel" in Dutch. (We specified Dutch "nl" as the default language in the YAML configuration above.)
    - [translate?q=Apple&q=Orange](translate?q=Apple&q=Orange) translates both Apple and Orange to "appel" and "Oranje"
- `?target=` is the optional target [language](https://cloud.google.com/translate/docs/languages) to translate to.
    - [translate?q=Apple&target=de](translate?q=Apple&target=de) returns "Apfel" in German
- `?source=` is the optional source [language](https://cloud.google.com/translate/docs/languages) to translate to.
    - [translate?q=Apfel&source=de&target=en](translate?q=Apfel&source=de&target=en) returns     "Apple" from German to English
    - Ignore it, or set it to an empty string, to auto-detect language.
      [translate?q=monde&source=&target=en](translate?q=monde&source=&target=en) auto-detects
      "monde" as French, and converts it to "world" in English

The response is a JSON list. Each entry is an object with the following keys:

- `q`: original string to translate (e.g. Apple)
- `t`: translated string (e.g. appel)
- `source`: source language (e.g. en -- which may have been auto-detected)
- `target`: target language (e.g. nl)

Example:

```json
[
  {"q":"Apple","t":"appel","source":"en","target":"nl"},
  {"q":"Orange","t":"Oranje","source":"en","target":"nl"}
]
```

When you specify a `cache:` section, it saves the responses. Future translation
requests are fetched from this cache.

## Translate cache

The `cache:` section accepts standard [FormHandler](../formhandler/) keys. For example:

```yaml
  # Store the data in a CSV file
  cache:
    url: $YAMLPATH/translate.csv

  # Store the data in an Excel file
  cache:
    url: $YAMLPATH/translate.xlsx
    sheet_name: translate

  # Store the data in a SQLAlchemy SQLite database
  cache:
    url: 'sqlite:///$YAMLPATH/translate.db'
    table: translate

  # Store the data in a SQLAlchemy SQLite database
  cache:
    url: 'postgresql://$USER:$PASS@server/db'
    table: translate
```

The data is stored in the cache as a table with same 4 columns as the response:
`q`, `t`, `source` and `target`.

[See the current cache data](cache?_format=html).

You can allow users to edit this cache using [FormHandler](../formhandler/).


## Translate function

You can translate strings in Python using `gramex.ml.translate`. For example:

```python
>>> import gramex.ml
>>> gramex.ml.translate('Apple', target='nl', key='...')
  source target      q      t
0     en     nl  Apple  appel

>>> gramex.ml.translate('Apple', 'Orange', target='nl', key='...')
  source target       q       t
0     en     nl   Apple   appel
1     en     nl  Orange  Oranje

>>> gramex.ml.translate('Apple', 'Orange', source='en', target='de', key='...')
  source target       q       t
0     en     de   Apple   Apfel
1     en     de  Orange  Orange
```

The response is a DataFrame. It has the same columns as the
[translate API](#translate-api).

This fetches data dynamically from Google Translate. You can specify a
[translate cache](#translate-cache) here too. For example:

```python
>>> cache = {'url': 'translate.xlsx', 'sheet_name': 'translate'}
>>> gramex.ml.translate('Apple', target='nl', cache=cache, key='...')  # Save data in cache
>>> gramex.ml.translate('Apple', target='nl', cache=cache, key='...')  # Fetch result from cache
```
