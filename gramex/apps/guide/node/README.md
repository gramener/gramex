---
title: Run JavaScript
prefix: node
...

Gramex can run JavaScript code via `node.js` using `gramex.pynode.node`.

[TOC]

## Run JavaScript

Gramex FunctionHandlers can run JavaScript code in node.js. Here is a simple example:

```python
from gramex.pynode import node
from tornado.gen import coroutine, Return

@coroutine
def total(handler):
    result = yield node.js('return Math.abs(x + y)', x=5, y=-10)    # Run code in JS
    raise Return(result)
```

This returns the result:

```json
{"error":null,"result":5}
```

<div class="example">
  <a class="example-demo" href="total">Run total in JS</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/node/nodeapp.py">Source</a>
</div>

## JavaScript conversion

Here is how `node.js()` works:

- **Run any JS code**. You can pass any JavaScript code to `node.js()`. Whatever
  the code returns is the result. For example, `node.js('return 1 + 2')` will
  return `3`.
- **Pass globals**. Any keyword arguments passed to `node.js()` become global
  variables. For example, `node.js('return x + y', x=1, y=2)` returns `3`.
- **Returns a Future**. You must use `yield node.js()`, decorate your function
  with `@tornado.gen.coroutine`, and return via `raise Return(...)`. Also see
  [asynchronous functions](../functionhandler/#asynchronous-functions).
- **Returns an object**. The result of `yield node.js()` is an object with 2
  keys:
    1. `result:` which contains the returned JavaScript value
    2. `error:` which is null if there is no error, otherwise the error object
       with 3 keys:
        1. `name` of the error
        2. `message` of the error
        3. `stack` has the full stack trace in JavaScript
- **Only JSON**. The input variables AND the output variable are in JSON.
  Anything that cannot be converted to JSON raises an error.
- **Callback support**. Instead of returning a value, you can call
  `callback(result)`. This return the result. This is useful for async JS.

Here is a practical example that uses the `juice` library to convert external
CSS into inline CSS:

```python
@coroutine
def inline_styles(handler):
    code = '''
      const juice = require('juice')          // This is JavaScript code
      return juice(html)                      // executed by node.js
    '''
    # We will take this HTML string and inline the styles
    html = '''
      <style>
        .heading { background-color: red; }
      </style>
      <h1 class="heading">Heading</h1>
    '''
    result = yield node.js(                   # Call node.js
        code,                                 # Run the JavaScript code
        html=html,                            # Pass html as a global variable
        lib='juice'
    )
    raise Return(result['result'])            # Return just the result
```

This returns

```html
<h1 class="heading" style="background-color: red;">Heading</h1>
```

<div class="example">
  <a class="example-demo" href="inline_styles">Run inline_styles</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/node/nodeapp.py">Source</a>
</div>
