---
title: LanguageTool App for Gramex
prefix: LanguageTool
...

[TOC]

## LanguageTool

LanguageTool is an Open Source proofreading software for English, French, German,
Polish, Russian, and [more than 20 other languages](https://languagetool.org/languages/).
It finds many errors that a simple spell checker cannot detect.
[See the README](https://github.com/languagetool-org/languagetool/blob/master/languagetool-standalone/README.md).

## Installation

To use LanguageTool, add the following to your `gramex.yaml`

```yaml
import:
  languagetool:
    path: $GRAMEXAPPS/languagetool/gramex.yaml
    YAMLURL: $YAMLURL/languagetool/
```

This mounts the app at [languagetool/](languagetool/).


## Usage

LanguageTool accepts two query parameters:

- `q`: The text to proofread
- `lang`: Language of the text (optional, default: `en-US`)

The JSON response consists of an object containing two keys:

* `errors`: enumerates grammatical and spelling errors in the input text. [Read more](http://wiki.languagetool.org/http-server#toc2) about the HTTP API.
* `correction`: contains the autocorrected version of the input text.

### Play with LanguageTool

<form class="ltform form-inline">
  <input type="text" class="form-control" placeholder="Enter text">
  <button class="btn btn-secondary ml-2">Check</button>
</form>
<div class="alert alert-success collapse my-2" role="alert">
  <p class="correction"></p>
  <pre class="language-json ltout"></code></pre>
</div>
<script>
  $('.ltform').on('submit', function (e) {
    e.preventDefault()
    $.ajax({
      url: "../languagetool/languagetool/",
      data: { q: $('.ltform input').val() }
    }).done(function (data) {
      $('.ltout').html(JSON.stringify(data, null, 4))
      $('.correction').html('Correction: <strong>' + data.correction + '</strong>')
      $('.alert-success').removeClass('collapse')
    })
  })
</script>

### Autocorrect with LanguageTool

LanguageTool may suggest _any_ number of corrections for _each_ error that it finds in the input text.
Gramex's wrapper for LanguageTool automatically applies the first correction it finds for each error,
thus generating the autocorrected version of the input text.
This output corresponds to the `correction` key in the [output](#usage) payload.
For finer control, users may explore the `errors` from the output.
Each error object contains potential corrections and the offset and length of the erroneous substring from the input text.

The following snippet demonstrates usage of the LanguageTool app assuming the app is mounted at `/languagetool` and Gramex is running locally at port 9988.

### Using LanguageTool with Ajax

The LanguageTool app in Gramex can be used with Ajax as follows:

```js
function checkGrammar(text) {
  $.ajax('languagetool/', {data: { q:  text } })
    .done(function (result) {
      console.log('Did you mean', result.correction)
    })
}
checkGrammar('Tooo many spellng mistaes!')
// Did you mean "Too many spelling mistakes!"
```


### LanguageTool API

LanguageTool can be used with a FunctionHandler as follows:

```python
import json
from tornado.gen import coroutine, Return
from tornado.httpclient import AsyncHTTPClient
from six.moves.urllib_parse import urlencode

@coroutine
def check_grammar(handler):
    client = AsyncHTTPClient()
    url = '{protocol}://{host}/languagetool/?'.format(**vars(handler.request))
    resp = yield client.fetch(url + urlencode({'q': handler.get_argument('q')}))
    result = json.loads(resp.body.decode('utf8'))
    raise Return(result['correction'])
```


## Examples

1. [The quick brown fox jamp over the lazy dog.](../languagetool/languagetool/?q=The quick brown fox jamp over the lazy dog.)
2. [how are you](../languagetool/languagetool/?q=how are you)
3. [I is fine.](../languagetool/languagetool/?q=I is fine.)


## Configuration

The LanguageTool app provides the following configurable [YAML variables](../config/#yaml-variables).

* `LT_PORT`: The port at which the LanguageTool subprocess runs (default: 8081)
* `LT_ALLOW_ORIGIN`: Set the Access-Control-Allow-Origin header in the HTTP response,
  used for direct (non-proxy) JavaScript-based access from browsers; (default : "*")
* `LT_VERSION`: Version of LanguageTool to use. (default: 4.4)
* `LT_TARGET`: Location at which to install LanguageTool. (default: `$GRAMEXDATA/languagetool`)
* `LT_SRC`: URL from which to download LanguageTool.
  (default: https://languagetool.org/download/LanguageTool-`${LT_VERSION}`.zip)
