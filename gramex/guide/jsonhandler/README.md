title: Gramex writes data

`JSONHandler` offers a persistent key-value store with an API inspired by
[Firebase](https://www.firebase.com/docs/rest/api/).

The following configuration creates a REST API endpoint at [data/](data/):

<iframe src="gramex.yaml"></iframe>

**NOTE**: The examples below use the [Fetch API][fetch-api] which is not
available on Internet Explorer. Use [jQuery.ajax][jquery-ajax] instead.

[fetch-api]: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch
[jquery-ajax]: http://api.jquery.com/jquery.ajax/

## GET - read data

You can read data via a GET request:

    fetch('data/')      // OUTPUT

You can read data from a specific key:

    fetch('data/y')     // OUTPUT

... or from a sub-key:

    fetch('data/y/a')   // OUTPUT

Missing keys return `null`:

    fetch('data/na')    // OUTPUT

Array values can be accessed via integer path elements:

    fetch('data/z/0')   // OUTPUT

## PUT - write data

You can write JSON data via a PUT request:

    fetch('data/new', {method: 'PUT', body: '{"x": 1}'})   // OUTPUT

This stores the JSON value as-is:

    fetch('data/new')   // OUTPUT

Incorrect values raise an error:

    fetch('data/invalid', {method: 'PUT', body: 'xxx'})

    // OUTPUT

## PATCH - update data

You can update existing data via PATCH. For example, the initial data:

    fetch('data/y')    // OUTPUT

... can be updated via PATCH:

    fetch('data/y', {method: 'PATCH', body: '{"c":3}'})   // OUTPUT

The result is:

    fetch('data/y')    // OUTPUT

## DELETE - remove data

You can delete any key via DELETE. For example, the initial data:

    fetch('data/y')   // OUTPUT

... can have keys removed:

    fetch('data/y/a', {method: 'DELETE'})     // OUTPUT

The result is:

    fetch('data/y')   // OUTPUT

## Method override

You can use the `X-HTTP-Method-Override` header to overide the method. For
example, this is the same as a PUT request:

    fetch('data/new?x-http-method-override=PUT', {
        method: 'POST',
        headers: new Headers({'X-HTTP-Method-Override': 'PUT'}),
        body: '1'
    })  // OUTPUT

You an also use the `?x-http-method-override=` query parameter:

    fetch('data/new?x-http-method-override=PUT', {
        method: 'POST',
        body: '1'
    })  // OUTPUT

**NOTE:** The method must be in capitals, e.g. `PUT`, `DELETE`, `PATCH`, etc.

<script>
function run(element) {
  var text = element.textContent
  if (text.match(/OUTPUT/))
    eval(text).then(function(response) {
      return response.text()
    }).then(function(result) {
      element.textContent = text.replace(/OUTPUT/, 'returns: ' + result)
    })
}

var pre = document.querySelectorAll('pre')
for (var i=0, l=pre.length; i<l; i++)
  run(pre[i])
</script>
