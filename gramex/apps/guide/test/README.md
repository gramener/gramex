---
title: Automate tests
prefix: Test
...

Gramex has a pytest plugin that simplifies automated testing.

[TOC]

## Quickstart

Create a `gramextest.yaml` in your app directory that looks like this:

```yaml
urltest:                            # Run tests on URLs without a browser
  - fetch: https://httpbin.org/get?x=1&y=abc
  - code: 200                       # HTTP status should be 200
  - headers:                        # Check the response HTTP headers
      Date: [endswith, GMT, UTC]    #   Date header ends with GMT or UTC
  - json:                           # Check the response as JSON
      args: {x: '1', y: abc}        #   {args: ...} matches this object
      args.x: '1'                   #   {args: {x: ...}} is '1'
```

Run `pytest -s -v`. This runs tests mentioned in `gramextest.yaml`.

<link rel="stylesheet" type="text/css" href="../node_modules/asciinema-player/resources/public/css/asciinema-player.css">
<asciinema-player src="pytest.rec" cols="100" rows="20" idle-time-limit="0.5" autoplay="1"></asciinema-player>

`gramextest.yaml` supports 2 kinds of tests:

- [URL tests](#url-test) that fetch URLs using Python and check the output
- [UI tests](#ui-test) that automate browser and UI interactions via Selenium

## URL test

URL tests begin with a `uitest:` section. These fetch URLs using Python and
check the output.

Here are a few examples:

### Check if page is live

```yaml
uitest:
  - fetch: https://httpbin.org/get    # Fetch this page
    code: 200                         # If it returns a status code 200, it's OK
```

`fetch`: fetch a URL. It accepts either a string URL or a dict of options:

- `url:` request URL
- `params`: URL parameters dict. `params: {x: [1, 2], y: 3}` => `?x=1&x=2&y=3
- `method`: HTTP method. Default: `GET`. `method: POST` sends a POST request
- `headers`: HTTP request headers dict. `headers: {User-Agent: ...}` sends
  the user-agent header
- `user`: Sets `handler.current_user` in Gramex via the `X-Gramex-User` HTTP
  header. E.g. `user: {email: user@example.org}`. This is encrypted using
  `app.settings.cookie_secret` from `gramex.yaml` in the current directory.

`code` [matches](#matching) the HTTP response status code. Some common codes are:

- `code: 200` to check if the page returns valid content
- `code: 302` to check if the page redirects elsewhere
- `code: [is, 401, 403]` to check if the user is not logged in (401) or cannot access the page (403)
- `code: 404` to check if a page is missing
- `code: 500` to check that the server reports an error

### Check if page has text

```yaml
uitest:
  - fetch: https://httpbin.org/get  # Fetch this page
  - text:                           # Check the response text
      - [has, args, headers]        #   Has at least one of these words
      - [has no, hello, world]      #   Has none of these words
```

`text:` matches the response as text. It supports [match operators](#matches).
For example:

- `text: [[has, hello], [not, world]]`: response must have "hello", not "world"
- `text: [match, year 20\d\d]`: response has "year 2000", "year 2001", ...


### Check JSON response

```yaml
uitest:
  - fetch: https://httpbin.org/get  # Fetch this page
  - json:                           # Check the response as JSON
      args: {x: '1', y: abc}        #   {args: ...} matches this object
      args.x: '1'                   #   {args: {x: ...}} is '1'
      args.y: [has, abc]            #   {args: {y: ...}} has the word 'abc'
```

`json:` matches the response as JSON. The value are a dict with keys as
[JMESPath](http://jmespath.org/tutorial.html) selectors, and values as
[matches](#matching).

- `@: [1, 2]}` means the response must exactly be `[1, 2]`. `@` is the response
- `args: {x: 1}` means `response.args == {"x": 1}`
- `args.headers: x` means `response.args.header == "x"`
- `headers."Accept-Encoding": x` means `response.headers["Accept-Encoding"] == "x"`

The values may be any [match operator](#matches).

### Check HTML response

```yaml
uitest:
  - fetch: https://httpbin.org/html # Fetch this page
  - html:                           # Check the response as HTML
      h1: [has, Herman]             #   All <h1> have "Herman" in the text
      p:first-child: [has, cool]    #   First <p> has the word "cool"
      p:                            #   All <p> elements
        class: null                 #     have no class
        .text: [has, cool]          #     and have "cool" in the text
```

`html:` matches the response as HTML. The values are a dict with keys as
[CSS3 selectors](https://www.w3.org/TR/selectors-3/) (not XPath) and values as
[matches](#matching), or dicts of attribute-[matches](#matching).

- `h1: Title`: All H1 tags' text are "Title"
- `h2:first-child: Subtitle`: The first subtitle text is "Subtitle"
- `li.item: [has, Product]`: Each `<li class="item">` has the text "Product"
- `li.item: {class: [has, item]}`: Each `<li class="item">` has the class "item"
- `a: {.text: Link, href: true}`: Each `<a>` has text "Link" and has a href attribute
- `a: {.length: 10}`: There are 10 `<a>` elements

### Check HTTP headers

```yaml
uitest:
  - fetch: https://httpbin.org/get  # Fetch this page
  - headers:                        # Check the response HTTP headers
      Server: true                  #   Server header is present
      Nonexistent: null             #   Nonexistent header is missing
      Date: [endswith, GMT, UTC]    #   Date header ends with GMT or UTC
```

The keys under `header:` match the HTTP header name. The values may be any
[match operator](#matches).

`headers:` matches the HTTP response headers. The values are a dict with keys as
HTTP headers and values as [matches](#matching).

- `Server: true`: response must have a Server header
- `Server: [starts with, Gramex/]`: Server header starts with "Gramex/"

## UI test

UI tests automate browser and UI interactions via Selenium.

### Set up browsers

To set up [UI testing](#ui-test), define a `browsers:` section:

```yaml
# Enable only the browsers you need, and install the drivers
browsers:
  Chrome: true
  Firefox: true
  Edge: true
  Ie: true
  Safari: true
  PhantomJS: true
```

Read how to [download the drivers](https://www.seleniumhq.org/download/) and add
them to your PATH.

Some browsers support additional options. Here is the complete list of options:

```yaml
browsers:
  Chrome:
    headless: true    # Run without displaying browser, in headless mode
    mobile:           # Enable mobileEmulation option
      deviceName: iPhone 6/7/8
  Firefox:
    headless: true    # Run without displaying browser, in headless mode
```

### Check content on page

```yaml
uitest:
  - fetch: https://www.google.com/  # Fetch this URL in the browser
  - title: Google                   # Title should match Google
  - title: [starts with, Goo]       # Title should start with "Goo"
  - find a[href*=privacy]:          # Find the first matching CSS selector
      .text: Privacy                #   The text should match "Privacy"
  - find xpath //input[@title]:     # Find the first matching XPath selector
      name: 'q'                     #   The attribute name= should be "q"
```

`fetch`: fetches the URL via a GET request

`title: <text>`: checks if the document.title [matches the text](#matches).

- `title: Google` => page title must be Google
- `title: [starts with, Goo]` => page title must start with Goo

`find <selector>: {<key>: <value>, ...}` tests the first node matching the
[selector](#selectors). For example:

- `find .item: {.text: hello}` => first `.item` has text exactly as "hello".
- `find .item: {.text: [has, hello]}` => first `.item` contains the text "hello"

The `<selector>` can be CSS (e.g. `find h1.heading`) or XPath (e.g. `find //h1[@class="heading]`)

- `find a.item: ...` => match `<a class="item">`
- `find xpath //a[contains(@class, "item")]: ...` => match `<a class="item">`

The key can be `.text`, which matches the full text content of the node.

- `find .item: {.text: hello}` => match `<p>hello</p>`
- `find .item: {.text: [has, hello]}` => match `<p> hello <b>world</b></p>`

Checking `.text` is the most common use. So you can skip it, and directly specify the value.

- `find .item: hello` => match `<p>hello</p>`
- `find .item: [has, hello]` => match `<p> hello <b>world</b></p>`

The key can be any attribute, like `id`, `class`, etc.

- `find .item: {id: root}` => match `<div class="item" id="root">`
- `find .item: {name: email}` => match `<input class="item" name="email">`

If the key begins with `:`, it matches a property, like `:value`.

- `find .item: {:value: hello}` => matches `<input class="item">` if the value entered is "hello"

If the key is `.length`, it checks the number of nodes matched.

- `find .item: {.length: 3}` => there are 3 `.item` elements
- `find .item: {.length: [greater than, 5]}` => there are 5+ `.item` elements

If the value is `true` or `false`, it checks if the element is present or absent.

- `find .item: true` => page must have a `.item` [selector](#selectors)
- `find .item: false` => page must not have a `.item` [selector](#selectors).
  (You may use `null` instead of `false`)

### Printing

```yaml
uitest:
  - print: .item            # Print the outer HTML of all `.item`s
  - print: xpath //h1       # Print the outer HTML of all H1s
```

`print: <selector>` prints the outer HTML of all matching selectors. This is
useful if the `find:` does not match, and you don't know why, or just want to
see what elements are available.


### Interact with the page

```yaml
uitest:
  - fetch: https://www.google.com/                  # Fetch this URL in the browser
  - clear: xpath //input[@title]                    # Clear existing input text
  - type xpath //input[@title]: gramener            # Type "gramener" in the input
  - hover: xpath //input[@value='Google Search']    # Hover over the Google Search button
  - click: xpath //input[@value='Google Search']    # Click on the Google Search button
```

`click: <selector>`: clicks a [CSS/XPath selector](#selectors).

- `click button.submit`: clicks `<button class="submit">`
- `click xpath //button[text()="Submit"]`: clicks `<button>Submit</button>`

`type <selector>: <text>`: types the text into the [CSS/XPath selector](#selectors)
(if it's an input).

`hover: <selector>`: hover over a [CSS/XPath selector](#selectors).

- `hover button.submit`: clicks `<button class="submit">`
- `hover xpath //button[text()="Submit"]`: clicks `<button>Submit</button>`

`clear: <selector>`: clears the text in the [CSS/XPath selector](#selectors)
(if it's an input).

`scroll: <selector>`: scroll a [CSS/XPath selector](#selectors) into view.

### Interact with the browser

```yaml
uitest:
  - fetch: https://www.google.com/    # Fetch this URL in the browser
  - resize: [800, 600]                # Resize to 800x600
  - fetch: https://gramener.com/      # Fetch another page
  - back: 1                           # Go back 1 page
  - forward: 1                        # Go forward 1 page
```

`resize: [width, height]` resizes the browser window. `width` and `height` are set in pixels.

- `resize: [800, 600]` resizes to 800px by 600px
- `resize: max` maximizes window. **Warning** On remote servers, screen size is unknown.

`back: <n>`: goes back `n` pages

`forward: <n>`: goes forward `n` pages

### Execute code

```yaml
uitest:
  # Run this in Python
  - python:
      import gramex.cache                     # Import any module
      data = gramex.cache.open('data.csv')    # Run any code
      y = data['col'][0]          # Variables persist through the test
      assert y > 0                # Assert conditions in Python
  # Run this in JavaScript
  - script:
      - window.x = y + 1          # Python variables are available in JS
      - return window.x: 1        # Return a value, and check if it is correct
```

`python:` runs Python code.

- `python: print(x)` prints the value of the variable "x"
- `python: x = 2` sets the variable x to 2. This is also available in `script:` as a global

`script:` is a list of JavaScript commands. If it's a string, runs the code. If it's a dict, checks the return values.

- `script: x = 1` sets `window.x` to 1. This is also available in `python:`
- `script: {"return document.title": [has, Gramener]}` checks if `document.title`
  has "Gramener"


## Running tests

To run a test suite, just run `pytest -s -v`. It looks for `gramextest.yaml`
under the current or `tests/` directory and executes the tests.

You can break up tests into multiple `gramextest.*.yaml` files. For example:

- `gramextest.page1.yaml`
- `gramextest.page1.login.yaml`
- `gramextest.page1.search.yaml`
- `gramextest.page2.yaml`
- etc

`pytest -s -v` will run the tests across all of these.

The following command line options are useful:

- `-v` prints the name of each test as it runs
- `-s` prints any print statements in the application directly
- `--pdb` enters debug mode on the first error
- `--tb=no` disables tracebacks.
  `--tb=line` prints 1 line tracebacks.
  `--tb=short` prints short tracebacks.

### Waiting

Actions may take time to perform -- e.g. JavaScript rendering in
[`uitest`](#ui-test). You can wait for certain conditions.

```yaml
uitest:
  - wait: 10                # Wait for 10 seconds
  - wait:
      selector: .chart      # Wait until .chart selector is visible on screen
  - wait:
      script: window.done   # Wait until the page sets window.done to true
  - wait:
      selector: xpath //h3  # Wait for <h3> element
      timeout: 30             #   for a maximum of 30 seconds (default: 10s)
  - wait:
      script: window.done   # Wait until window.done is true
      timeout: 30           #   for a maximum of 30 seconds (default: 10s)
```

The selector may be a [CSS/XPath selector](#selectors).


### Skipping

You can skip tests using `skip: true`. This starts skipping tests. `skip: false`
stops skipping tests. For example:

```yaml
uitest:
  - ...             #   Run this
  - skip: true      # Start skipping
  - ...             #   Skip this
  - ...             #   Skip this
  - skip: false     # Stop skipping
  - ...             #   Run this
  - ...             #   Run this
```


### Debugging

You can stop the test and enter debug mode using `debug`. This lets you inspect
variables in the browser or server, and see why test cases fail.

```yaml
uitest:
  - fetch: ...
  - debug           # Debug the next command
  - ...             #   pytest will pause the 1st action
  - ...             #   pytest WON'T pause the 2nd action
  - debug: true     # Debug EVERY future action
  - ...             #   pytest will pause every action
  - ...             #   pytest will pause every action
  - debug: false    # Stop debug mode
  - ...             #   pytest WON'T pause
  - debug: 2        # Debug the next 2 actions
  - ...             #   pytest will pause the 1st action
  - ...             #   pytest will pause the 2nd action
  - ...             #   pytest WON'T pause after that
```

If you want to stop debugging mid-way, type `mode.debug = 0` in the debugger.
This is the same as `debug: false`.

Run `pytest --pdb` to enter debug mode on the first error. This is useful when
you want to explore the browser state when an error occurs, and to correct your
test cases.


### Naming

By default, tests names are constructed using the actions in the test. For
example, this test:

```yaml
uitest:
  - fetch: https://www.google.com/
    title: Google
```

... gets a name `Chrome #001: fetch: "https://www.google.com/, ...`. This makes
it easy to identify which test is currently running (or failing.)

You can over-ride the name using `name:`. For example:

```yaml
uitest:
  - name: Check Google home page
    fetch: https://www.google.com/
    title: Google
```

... gets a name `Chrome #001: Check Google home page`. This makes it easier to
run specific tests by matching the name via `pytest -k 'pattern'`.

### Grouping

Test cases can be grouped using `mark:`. This makes it easier to selectively run
tests. For example:

```yaml
uitest:
  - mark: group1
  - ...             # This test belongs to group1
  - ...             # This test belongs to group1
  - mark: group2
  - ...             # This test belongs to group2
  - ...             # This test belongs to group2
```

- `pytest -m group1` to only run group1 tests.
- `pytest -m 'group1 or group2'` runs group1 or group2 tests, no others

### Run specific tests

You can run [specific tests](https://docs.pytest.org/en/latest/usage.html#specifying-tests-selecting-tests)
by mentioning its name. For example:

- `pytest -k "home-page"` -- run all tests matching `home-page`
- `pytest -k "home-page AND title"` -- run all tests matching `home-page` AND title

You can run [groups of tests](#grouping) using marks:

- `pytest -m group1` to only run group1 tests.
- `pytest -m 'group1 or group2'` runs group1 or group2 tests, no others


### Test reporting

Install the [pytest-sugar](https://pypi.org/project/pytest-sugar/) plugin to
improve the reporting. It shows progress better, and reports errors and failures
instantly.

Install the [pytest-html](https://pypi.org/project/pytest-html/) plugin to
report pytest output as HTML. Run by using `pytest --html=report.html`.

## Test specification

`urltest:` and `uitest:` are lists of actions to perform. An action can either
do something (like `fetch`, `click`, etc.) or test something (like `headers`,
`text`, etc.)

An action can be defined as a dict of `{command: options}`. For example, the
`fetch:` action can be defined as:

```yaml
urltest:
  - fetch: https://httpbin.org/get?x=1      # fetch: <url>
  - fetch:                                  # fetch: {url: <url>, options}
      url: https://httpbin.org/get
      params: {x: 1}
```

### Selectors

CSS and XPath selectors are both allowed wherever selectors are used in
[`uitest:`](#ui-test). XPath selectors begin with `xpath `. Otherwise, it's a
CSS selector.

- `h1`: CSS to select `<h1>`.
- `xpath //h1`: XPath to select `<h1>`.

Note: <strong>XPath SVG selectors are tricky</strong>. You need to provide a
namespace. Use CSS selectors instead.


### Matches

You can compare the result against a set of values in different ways. For
example, when testing the `text:` of a response, you can use:

- `text: value`: text is exactly equal to "value1"
- `text: true`: text is present
- `text: null`: text is not present
- `text: false`: text is false-y (empty string, zero, False, etc)

... or use a list of `[operator, value]`:

- `text: [is, value]`: text is exactly equal to "value1"
- `text: [has, value]`: text has the string "value"
- `text: [match, v.*e]`: text matches the regular expression "v.*e"
- `text: [starts with, val]`: text starts with "val"
- `text: [ends with, ue]`: text ends with "ue"
- `text: [is not, abc]`: text is not exactly equal to "abc"
- `text: [has no, abc]`: text does not have the string "abc"

... or use a list of `[operator, value1, value2, ...]`.

- `text: [is, value1, value2]`: text is either "value1" or "value2"
- `text: [has, value1, value2]`: text has the string "value1" or "value2"
- `text: [matches, v.*, .*e]`: text matches the regular expression "v.*" or ".*e"
- `text: [starts with, val1, val2]`: text starts with "val1" or "val2"
- `text: [ends with, ue, lue]`: text ends with "ue" or "lue"
- `text: [is not, abc, def]`: text is not exactly equal to "abc" nor "def"
- `text: [does not have, abc, def]`: text does not have the string "abc" nor "def"
- `text: [does not match, a.*, b.*]`: text does not match regex "a.*" nor "b.*"

These matches are **case-insenstive** and **ignore whitespace**. To use
case-sensitive and exact matches, use operators in CAPS. For example:

- `text: [IS, value1]` matches only lowercase "value1", but
- `text: [is, value1]` matches "VALUE1", "Value1", "value1", etc.
- Similarly for other operators.

You can apply multiple operators to a check. The test passes if ALL of them
pass. For example:

```yaml
text: [
  [has, username],                    # The word Username must be present
  [has, password],                    # Password must also be present
  [has no, forbidden, unauthorized],  # Neither forbidden nor unauthorized must match
  [match, login.*button],             # "login" followed by "button" should be present
]
```

These matches can be used in *any* value that we test for, such as `code:`,
`text:`, `headers:` keys, `json:` keys, etc.

For numbers, you can also use `>`, `>=`, `<`, `<=` as operators. For example:

```yaml
json:
  args.count: [['>', 30], ['<=', 50]]    # args.count > 30, and args.count <= 50
```


<script src="../node_modules/asciinema-player/resources/public/js/asciinema-player.js"></script>
