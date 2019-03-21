LanguageTool App for Gramex
===========================

Use [LanguageTool](https://languagetool.org) as a Gramex app.

[TOC]

LanguageTool
------------

LanguageTool is an Open Source proofreading software for English, French, German,
Polish, Russian, and [more than 20 other languages](https://languagetool.org/languages/).
It finds many errors that a simple spell checker cannot detect.

LanguageTool is freely available under the LGPL 2.1 or later.

For more information, please see our homepage at https://languagetool.org,
[this README](https://github.com/languagetool-org/languagetool/blob/master/languagetool-standalone/README.md),
and [CHANGES](https://github.com/languagetool-org/languagetool/blob/master/languagetool-standalone/CHANGES.md).

Installation
------------

To use LanguageTool, add the following to your `gramex.yaml`

```yaml
import:
  languagetool:
    path: $GRAMEXAPPS/languagetool/gramex.yaml
    YAMLURL: $YAMLURL/languagetool/
```

This mounts the app at [languagetool/](languagetool/).


Usage
-----

The LanguageTool app consists of a [`FunctionHandler`](../functionhandler) which
accepts two query parameters:

* `q`: The text to proofreadh
* `lang`: Language of the text (optional, default: 'en-US')

The JSON response consists of an object containing two keys:

* `errors`: enumerates grammatical and spelling errors in the input text. [Read more](http://wiki.languagetool.org/http-server#toc2) about the HTTP API.
* `correction`: contains the autocorrected version of the input text.


### Autocorrect with LanguageTool

LanguageTool may suggest _any_ number of corrections for _each_ error that it finds in the input text.
Gramex's wrapper for LanguageTool automatically applies the first correction it finds for each error,
thus generating the autocorrected version of the input text.
This output corresponds to the `correction` key in the [output](#usage) payload.
For finer control, users may explore the `errors` from the output.
Each error object contains potential corrections and the offset and length of the erroneous substring from the input text.

The following snippet demonstrates usage of the LanguageTool app assuming the app is mounted at `/languagetool` and Gramex is running locally at port 9988.

### Using LanguageTool with Ajax Requests

The LanguageTool app in Gramex can be used with Ajax as follows:

```js
function checkGrammar(text) {
  $.ajax({
    url: "/languagetool/?q=" + encodeURIComponent(text),
    type: "GET",
    success: function (e) {
      console.log(`Did you mean "${e.correction}"?`)
    }
  })
}
checkGrammar('Tooooo many spellng mistaes!')
// Did you mean "Too many spelling mistakes!"?
```


### Using LanguageTool with Tornado coroutines

```python
import json
from tornado.gen import coroutine, Return, IOLoop
from tornado.httpclient import AsyncHTTPClient
from six.moves.urllib_parse import urlencode

URL = "http://localhost:9988/languagetool/?"


@coroutine
def check_grammar(text, lang='en-us'):
    url = URL + urlencode({'q': text, 'lang': lang})
    client = AsyncHTTPClient()
    result = yield client.fetch(url)
    raise Return(result.body)


@coroutine
def main():
    sentence = "Hows this with no apostrophy?"
    resp = yield check_grammar(sentence)
    resp = json.loads(resp.decode('utf8'))
    print(resp['correction'])  # How's this with no apostrophe?

    for error in resp['errors']:
        offset, limit = error['offset'], error['length']
        print(error['message'], "at", sentence[offset:(offset + limit)])

    # Possible spelling mistake found at Hows
    # Possible spelling mistake found at apostrophy


IOLoop.current().run_sync(lambda: main())
```


Examples
--------
1. [The quick brown fox jamp over the lazy dog.](../languagetool/languagetool/?q=The quick brown fox jamp over the lazy dog.)
2. [how are you](../languagetool/languagetool/?q=how are you)
3. [I is fine.](../languagetool/languagetool/?q=I is fine.)



Configuration
-------------

The LanguageTool app provides the following configurable [YAML variables](../config/#yaml-variables).

* `LT_PORT`: The port at which the LanguageTool subprocess runs (default: 8081)
* `LT_ALLOW_ORIGIN`: Set the Access-Control-Allow-Origin header in the HTTP response,
  used for direct (non-proxy) JavaScript-based access from browsers; (default : "*")
* `LT_VERSION`: Version of LanguageTool to use. (default: 4.4)
* `LT_TARGET`: Location at which to install LanguageTool. (default: `$GRAMEXDATA/languagetool`)
* `LT_SRC`: URL from which to download LanguageTool.
  (default: https://languagetool.org/download/LanguageTool-`${LT_VERSION}`.zip)


Play with LanguageTool
----------------------

<div class="input-group mb-2 mb-sm-0">
  <input type="text" class="form-control border-left-0" id="ltform" placeholder="Enter text">
  <span class="input-group-btn">
    <button class="btn btn-secondary" id="checkbtn">Check</button>
  </span>
</div>
<div class="alert alert-success collapse" role="alert">
  <button type="button" class="close" data-toggle="collapse" aria-label="Close" id="closebtn">
    <span aria-hidden="true">&times;</span>
  </button>
  <div class="viewsource-wraper">
    <pre class="language-json">
      <code class="language-json" id="ltout"></code>
    </pre>
  </div>
</div>
<script>
  $('#closebtn').on('click', function () {$('.alert').hide()})
  function checkGrammar() {
    var text = document.getElementById('ltform').value
    $.ajax({
      url: "../languagetool/languagetool/?q=" + encodeURIComponent(text),
      type: "GET",
      success: function(e) {
        document.getElementById('ltout').innerText = JSON.stringify(e, null, 4)
        $('.alert-success').show()
      }
    })
  }
  document.getElementById('checkbtn').addEventListener('click', checkGrammar)
</script>
