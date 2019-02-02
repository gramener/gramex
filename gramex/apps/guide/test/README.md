---
title: Automate tests
prefix: Test
...

Create a `gramextest.yaml` in your app directory and run `pytest`. This runs
tests mentioned in `gramextest.yaml`.

Here's a sample [gramextest.yaml](gramextest.yaml):

<iframe frameborder="0" src="gramextest.yaml.source"></iframe>

Run it using `pytest` or `pytest gramextest.yaml`:

<link rel="stylesheet" type="text/css" href="../node_modules/asciinema-player/resources/public/css/asciinema-player.css">
<asciinema-player src="pytest.rec" cols="100" rows="20" idle-time-limit="0.5" autoplay="1"></asciinema-player>

You can run [specific tests](https://docs.pytest.org/en/latest/usage.html#specifying-tests-selecting-tests)
by mentioning its name. For example:

- `pytest -k urltest` -- run all `urltest:`
- `pytest -k urltest:4` -- run the 4th `urltest`
- `pytest -k uitest:3:Chrome` -- run the 3rd `uitest` on Chrome

## Structure

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

## URL test

Here are the `urltest:` actions:

- `fetch`: fetch a URL. Options:
    - `url:` request URL
    - `params`: URL parameters dict. `params: {x: [1, 2], y: 3}` => `?x=1&x=2&y=3
    - `method`: HTTP method. Default: `GET`. `method: POST` sends a POST request
    - `headers`: HTTP request headers dict. `headers: {User-Agent: ...}` sends
      the user-agent header
    - `user`: Sets `handler.current_user` in Gramex via the `X-Gramex-User` HTTP
      header. E.g. `user: {email: user@example.org}`. This is encrypted using
      `app.settings.cookie_secret` from `gramex.yaml` in the current directory.
- `code`: [matches](#matching) the HTTP response status code.
    - `code: 200`: response must be HTTP 200
    - `code: [in, 200, 302]`: response can be HTTP 200 or 302
- `headers`: matches the HTTP response headers. This is a dict. Keys are header
  names. Values are [matches](#matching).
    - `Server: true`: response must have a Server header
    - `Server: [starts with, Gramex/]`: Server header starts with "Gramex/"
- `text`: [matches](#matching) the response as text.
    - `text: [[has, hello], [not, world]]`: response must have "hello", not "world"
    - `text: [match, year 20\d\d]`: response has "year 2000", "year 2001", ...
- `json`: matches the response as JSON. This is a dict. Keys are
  [JMESPath](http://jmespath.org/tutorial.html) selectors. Values are
  [matches](#matching).
    - `@: [1, 2]}`: `response == [1, 2]`
    - `args: {x: 1}`: `response.args == {"x": 1}`
    - `args.headers: x`: `response.args.header == "x"`
    - `headers."Accept-Encoding": x`: `response.headers["Accept-Encoding"] == "x"`
- `html`: matches the response as HTML. This is a dict.
  Keys are [CSS3 selectors](https://www.w3.org/TR/selectors-3/).
  Values are [matches](#matching), or dicts of attribute-[matches](#matching).
  Here are some examples:
    - `h1: Title`: All H1 tags' text are "Title"
    - `h2:first-child: Subtitle`: The first subtitle text is "Subtitle"
    - `li.item: [has, Product]`: Each `<li class="item">` has the text "Product"
    - `li.item: {class: [has, item]}`: Each `<li class="item">` has the class "item"
    - `a: {.text: Link, href: true}`: Each `<a>` has text "Link" and has a href attribute
    - `a: {.length: 10}`: There are 10 `<a>` elements

## Browsers

To set up [UI testing](#ui-test) (or browser testing), define a `browsers:` section:

```yaml
browsers:
    Chrome: true
    Firefox: true
    Edge: true
    # ...
```

Read how to [download the drivers](https://www.seleniumhq.org/download/) and add
them to your PATH.

# UI test

Once you set up the [browsers](#browsers), you can use thes `uitest:` actions:

- `fetch`: fetches the URL via a GET request
- `find <selector>`: finds a CSS/XPath selector and tests its attributes.
    - `find .item: true` => page must have a `.item` selector
    - `find .item: false` => page must not have a `.item` selector.
      (You may use `null` instead of `false`)
    - `find .item: hello` => first `.item` selector matches "hello"
    - `find .item: [has, hello]` => first `.item` selector has "hello"
    - `find .item: {id: root}` => first `.item` selector has id="root".
      Attributes are accessed via `<attribute-name>`.
    - `find input: {":value": ok}` => first `input` selector has value "ok".
      Properties are accessed via `:<property-name>` with a colon prefix `:`.
    - `find input: {.text: hello}` => first `.item` selector matches "hello".
      HTMLElement attrs are accessed via `.<attr-name>` with a dot prefix `.`.
    - `find .item: {.length: 3}` => There are 3 `.item` selectors on the page.
    - `find xpath //a[contains(@text, "Gramex")]: true` => there's a link having text "Gramex"
- `click: <selector>`: clicks a CSS/XPath selector.
    - `click button.submit`: clicks `<button class="submit">`
    - `click xpath //button[text()="Submit"]`: clicks `<button>Submit</button>`
- `back: <n>` goes back `n` pages in history
- `forward: <n>` goes forward `n` pages in history
- `scroll: <selector>` scrolls the CSS/XPath selector into view
- `wait: <n>` waits for `n` seconds
- `script:`: runs JavaScript and checks the results. This is a list
    - `- window.x = 1` sets `window.x` to 1
    - `- "return document.title": [has, Gramener]` [matches](#matching) the document title
- `type <selector>: <text>`: types the text into the CSS/XPath selector (if it's an input)
- `screenshot: <path>`:
- `submit: <selector>`: TODO: submits the form at selector
- `clear: <selector>`: TODO: clears the form at selector

Selectors can be CSS or XPath. Selectors default to CSS. Use `xpath <selector>`
for XPath selectors. For example:

- `find a` - matches the first `<a>` element using a CSS selector
- `find xpath //a` - also matches the first `<a>` element, but using an XPath selector


## Matches

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

TODO: Document adding new operators


## Examples


Open Google, search for Gramex, press submit, and check the results.

```yaml
url: http://127.0.0.1:1234/
test:
    - ui:
        # TODO: relative URL
        - open /
        # TODO: typing
        - type input: Gramex
        # TODO: text implies true
        - test //[@id=searchresults]//a[contains(@text, 'Google auth')]
```

<script src="../node_modules/asciinema-player/resources/public/js/asciinema-player.js"></script>
