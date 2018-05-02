---
title: JSONHandler writes JSON data
prefix: JSONHandler
...

[JSONHandler][jsonhandler] offers a persistent key-value store with an API inspired by
[Firebase](https://www.firebase.com/docs/rest/api/). For example:

    url:
        jsonhandler-data:
            pattern: /$YAMLURL/data/(.*)
            handler: JSONHandler
            kwargs:
                # Optional location where JSON data is persisted.
                # (If path is not specified, the JSON data is not persisted.
                #  When Gramex restarts, the data is lost.)
                path: $GRAMEXDATA/jsonhandler.json

                # Optional initial dataset to be used -- used only if path is
                # not specified. (Defaults to null.)
                data: {x: 1}

The examples below use [jQuery.ajax][jquery-ajax] and the [cookie.js][cookie.js]
libraries.

[jquery-ajax]: http://api.jquery.com/jquery.ajax/
[cookie.js]: https://github.com/florian/cookie.js
[jsonhandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.JSONHandler

<script src="https://cdnjs.cloudflare.com/ajax/libs/cookie.js/1.2.0/cookie.min.js"></script>


## GET - read data

You can read data via a GET request:

```js
$.ajax('data/')
// OUTPUT
```

You can read data from a specific key:

```js
$.ajax('data/y')    // OUTPUT
```

... or from a sub-key:

```js
$.ajax('data/y/a')  // OUTPUT
```

Missing keys return `null`:

```js
$.ajax('data/na')   // OUTPUT
```

Array values can be accessed via integer path elements:

```js
$.ajax('data/z/0')  // OUTPUT
```


## PUT - write data

You can write JSON data via a PUT request.

```js
$.ajax('data/new', {
  method: 'PUT',
  data: '{"x": 1}'
})  // OUTPUT
```

This stores the JSON value as-is:

```js
$.ajax('data/new')        // OUTPUT
```

Incorrect values raise an error:

```js
$.ajax('data/invalid', {
  method: 'PUT',
  data: 'xxx'             // Invalid JSON
})  // OUTPUT
```

## POST - add data

You can add new records via a POST request. First, let's start with an empty object.

```js
$.ajax('data/list', {method: 'DELETE'})    // OUTPUT
```

... and POST a record to it.

```js
$.ajax('data/list', {
  method: 'POST',
  data: '{"x": 1}'
})                      // OUTPUT
```

Records are added with a unique random key. The final dataset looks like this:

```js
$.ajax('data/list')
// OUTPUT
```

## PATCH - update data

You can update existing data via PATCH. For example, the initial data:

```js
$.ajax('data/y')        // OUTPUT
```

... can be updated via PATCH:

```js
$.ajax('data/y', {
  method: 'PATCH',
  data: '{"c":3}'
})                      // OUTPUT
```

The result is:

```js
$.ajax('data/y')        // OUTPUT
```

## DELETE - remove data

You can delete any key via DELETE. For example, the initial data:

```js
$.ajax('data/y')        // OUTPUT
```

... can have keys removed:

```js
$.ajax('data/y/a', {
  method: 'DELETE'
})                      // OUTPUT
```

The result is:

```js
$.ajax('data/y')        // OUTPUT
```

## Method override

You can use the `X-HTTP-Method-Override` header to override the method. For
example, this is the same as a PUT request:

```js
$.ajax('data/new', {
    method: 'POST',
    headers: {
      'X-HTTP-Method-Override': 'PUT',
    },
    data: '1'
})  // OUTPUT
```

You an also use the `?x-http-method-override=` query parameter:

```js
$.ajax('data/new?x-http-method-override=PUT', {
    method: 'POST',
    data: '1'
})  // OUTPUT
```

**NOTE:** The method must be in capitals, e.g. `PUT`, `DELETE`, `PATCH`, etc.

<script>
var pre = [].slice.call(document.querySelectorAll('pre'))
function next() {
  var element = pre.shift()
  var text = element.textContent
  if (text.match(/RUN/))
    return eval.call(this, text).always(next)
  if (!text.match(/OUTPUT/))
    return setTimeout(next, 0)
  if (text.match(/\$.ajax/)) {
    eval(text)
      .always(function(result) {
        element.innerHTML = element.innerHTML.replace(/OUTPUT/, 'returns: ' + JSON.stringify(result))
        if (pre.length > 0) { next() }
      })
  } else if (text.match(/fetch/)) {
    eval(text).then(function(response) {
      return response.text()
    }).then(function(result) {
      element.innerHTML = element.innerHTML.replace(/OUTPUT/, 'returns: ' + result)
      if (pre.length > 0) {
        next()
      }
    })
  }
}
next()
</script>
