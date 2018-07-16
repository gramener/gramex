from gramex.pynode import node
from tornado.gen import coroutine, Return


@coroutine
def total(handler):
    result = yield node.js('return Math.abs(x + y)', x=5, y=-10)    # Run code in JS
    raise Return(result)


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
    raise Return(result['result'])
