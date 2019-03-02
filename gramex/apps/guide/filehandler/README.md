---
title: FileHandler renders files
prefix: FileHandler
...

[TOC]

[gramex.yaml](../gramex.yaml.source) uses the [FileHandler][filehandler]
to display files. This folder uses the following configuration:

```yaml
url:
  markdown:
    pattern: /$YAMLURL/(.*)               # Any URL under the current gramex.yaml folder
    handler: FileHandler                  # uses this handler
    kwargs:
      path: $YAMLPATH                     # Serve files from this YAML file's directory
      default_filename: README.md         # using README.md as default
      index: true                         # List files if README.md is missing
```

Any file under the current folder is shown as is. If a directory has a
`README.md`, that is shown by default.

`$YAMLURL` is replaced by the current URL's path (in this case, `/filehandler/`)
and `$YAMLPATH` is replaced by the directory of `gramex.yaml`.

**Note**: Gramex comes with a `default` URL handler that automatically serves
files from the home directory of your folder. To prevent that, override the
`default` pattern:

```yaml
url:
  default:                              # This overrides the default URL handler
    pattern: ...
```

## Directory listing

`index: true` lists all files in the directory if the `default_filename` is
missing. To customise the directory listing, specify `index_template: filename`.
This file will be shown as HTML, with `$path` replaced by the directory's
absolute path, and `$body` replaced by a list of all files in that directory.

For example,

```yaml
url:
  static:
    pattern: /$YAMLURL/static/(.*)        # Any URL starting with /static/
    handler: FileHandler                  # uses this handler
    kwargs:
      path: $YAMLPATH/static/             # Serve files from static/
      default_filename: index.html        # using index.html as default
      index: true                         # List files if index.html is missing
      index_template: $YAMLPATH/template.html   # Use template.html to list directory
```

Here is a trivial `template.html`:

```html
<h1>$path</h1>
$body
```


## Redirecting files

You can specify any URL for any file. For example, to map the file
`filehandler/data.csv` to the URL `/filehandler/data`, use this configuration:

```yaml
    pattern: /$YAMLURL/filehandler/data     # The URL /filehandler/data
    handler: FileHandler                    # uses this handler
    kwargs:
      path: $YAMLPATH/filehandler/data.csv  # and maps to this file
```

You can also map regular expressions to file patterns. For example, to add a
`.yaml` extension automatically to a path, use:

```yaml
url:
  yaml-extensions:
    pattern: /$YAMLURL/yaml/(.*)  # yaml/anything
    handler: FileHandler
    kwargs:
      path: $YAMLPATH/*.yaml      # becomes anything.yaml, replacing the * here
```

For example, [yaml/gramex](yaml/gramex) actually renders [gramex.yaml](gramex.yaml.source).

To replace `.html` extension with `.yaml`, use:

```yaml
url:
  replace-html-with-yaml:
    pattern: /$YAMLURL/(.*)\\.html  # Note the double backslash instead of single backslash
    handler: FileHandler
    kwargs:
      path: $YAMLPATH/*.yaml        # The part in brackets replaces the * here
```

For more complex mappings, use a dictionary of regular expression mappings:

```yaml
url:
  mapping:
    pattern: /$YAMLURL/((foo|bar)/.*)       # /foo/anything and /bar/anything matches
    handler: FileHandler
    kwargs:
      path:                                 # If path: is a dict, it's treated as a mapping
        'foo/': $YAMLPATH/foo.html                     # /foo/ -> foo.html
        'bar/': $YAMLPATH/bar.html                     # /bar/  -> bar.html
        'foo/(.*)': $YAMLPATH/foo/{0}.html             # /foo/x -> foo/x.html
        'bar/(?P<file>.*)': $YAMLPATH/bar/{file}.html  # /bar/x  -> bar/x.html
```

The mapping has keys that are regular expressions. They must match the part of
the URL in brackets. (If there are multiple brackets, match the first one.)
Values are file paths. They are formatted as string templates using the regular
expression match groups and URL query parameters. So:

- `{0}` matches the first capture group (in brackets, like `(.*)`),
  `{1}` matches the second capture group, etc.
- `{file}` matches the named capture group `(?P<file>.*)`, etc
- If there's a URL query parameter `?file=`, the first value that replaces
  `{file}` -- but only if there is no such named capture group

When using URL query parameters, you should provide default values in case the
request does not pass the parameter. You can do this using `default:`

```yaml
url:
  mapping:
    pattern: /$YAMLURL/                     # Home page
    handler: FileHandler
    kwargs:
      path:                                 # If path: is a dict, it's treated as a mapping
        '': $YAMLPATH/{dir}/{file}.{ext}    #  /?dir=foo&file=bar&ext=txt -> foo/bar.txt
      default:
        dir: ''             # ?dir= is the default
        file: index         # ?file=index is the default
        ext: html           # ?ext=html is the default
```


## Caching

See how to cache [static files](../cache/#static-files)

## File patterns

If you want to map a subset of files to a folder, you can mark them in the
pattern. For example, this configuration maps `/style.css` and `/script.js` to
the home directory. To ensure that this takes priority over others, you can add
a higher value to the `priority` (which defaults to 0.)

```yaml
url:
  assets:
    pattern: /(style.css|script.js)             # Any of these to URLs
    priority: 2                                 # Give it a higher priority
    handler: FileHandler                        # uses this handler
    kwargs:
      path: .                                   # Serve files from /
```

This can work across directories as well. For example, this maps the `static`
and `bower_components` and specifies a 1-day expiry for any files under them.

```yaml
url:
  static-files:
  # Any file under the current directory, starting with bower_components/
  # or with static/ is mapped to a FileHandler
  pattern: /$YAMLURL/(bower_components/.*|static/.*)
  handler: FileHandler
  kwargs:
    path: $YAMLPATH/                          # Base is the current directory
    headers:
      Cache-Control: public, max-age=86400    # Cache publicly for 1 day
```

## Ignore files

To prevent certain files from ever being served, specify the
`handlers.FileHandler.ignore` setting. By default, this is:

```yaml
handlers:
  FileHandler:
    ignore:
      - gramex.yaml     # Always ignore gramex.yaml in Filehandlers
      - ".*"            # Hide dotfiles
```

The `gramex.yaml` file and all files beginning with `.` will be hidden by
default. You can change the above setting in your `gramex.yaml` file.

You can customise this further via the `allow:` and `ignore:` configurations in
the handler. For example:

```yaml
url:
  unsafe-handler:
    pattern: "/(.*)"
    handler: FileHandler
    kwargs:
      path: .
      ignore:
        - '*.yaml'          # Ignore all YAML files
      allow:
        - public.yaml       # But allow public.yaml to be shown
```

Now `public.yaml` is accessible. But `gramex.yaml` will raise a HTTP 403 error.
The log reports `Disallow: "gramex.yaml". It matches "*.yaml"`.

If you import [deploy.yaml](../deploy/#security), FileHandler blocks all files
except specific white-listed exceptions.

## MIME types

The URL will be served with the MIME type of the file. CSV files have a MIME
type `text/csv` and a `Content-Disposition` set to download the file. You
can override these headers:

```yaml
    pattern: /filehandler/data
    handler: FileHandler
    kwargs:
        path: filehandler/data.csv
        headers:
            Content-Type: text/plain      # Display as plain text
            Content-Disposition: none     # Do not download the file
```

To convert a file type into an attachment, use:

```yaml
    pattern: /filehandler/data
    handler: FileHandler
    kwargs:
        path: filehandler/data.txt
        headers:
            Content-Type: text/plain
            Content-Disposition: attachment; filename=data.txt    # Save as data.txt
```

From **v1.23.1**, to serve different files with different MIME types, use file patterns:

```yaml
    pattern: /$YAMLURL/(.*)
    handler: FileHandler
    kwargs:
      path: $YAMLPATH
      headers:
        Content-Type: text/plain            # Default header
        "*.json":                           # Override headers on .json files
          Content-Type: application/json
        "json/**"                           # Override headers on json/ directory
          Content-Type: application/json
```

## Templates

The `template` configuration renders files as [Tornado templates][template]. To
serve a file as a Tornado template, use the following configuration:

```yaml
url:
  template:
    pattern: /page                  # The URL /page
    handler: FileHandler            # displays a file
    kwargs:
      path: page.html               # named page.html
      template: true                # rendered as a Tornado template
```

You can apply templates to specific file patterns. For example:

```yaml
url:
  template:
    pattern: /templates/(.*)
    handler: FileHandler
    kwargs:
      path: templates/          # Render files from this path
      # Specify ONE of the following
      template: '*.html'        # Only HTML files are rendered as templates
      template: 'template.*'    # Only template.* files are rendered as templates
      template: '*'             # Same as template: true
```

Template files can contain any template feature. Here's a sample `page.html`.

```html
<p>argument x is {{ handler.get_argument('x', None) }}</p>
<ul>
    {% for item in [1, 2, 3] %}<li>{{ item }}</li>{% end %}
</ul>
```

<div class="example">
  <a class="example-demo" href="template">Template example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/tree/master/gramex/apps/guide/filehandler/template.html">Source</a>
</div>

### Template syntax

Templates can use all variables in the [template syntax][template-syntax], like:

- `handler`: the current request handler object
- `request`: alias for `handler.request`
- `current_user`: alias for `handler.current_user`

### Sub-templates

Templates import sub-templates using `{% include path/to/template.html %}`.

- The path is relative to the parent template.
- All parent template variables are available in the sub-template.

For example:

```html
This imports navbar.html in-place as a template.
{% set title, menu = 'App name', ['Home', 'Dashboard'] %}
{% include path/relative/to/template/navbar.html %}

navbar.html can use title and menu variables.
```

### UI Modules

Templates import [modules](https://www.tornadoweb.org/en/stable/guide/templates.html#ui-modules)
using `{% module Template('path/to/template.html', **kwargs) %}`.

- The path is relative to the FileHandler root path (which may be different from the parenttemplate
- Only the variables passed are available to the sub-template.

For example:

```html
This import navbar.html in-place as a template.
{% module Template('path/relative/to/filehandler/navbar.html',
      title='App name',
      menu=['Home', 'Dashboard'])
%}
```

Modules can add CSS and JS to the parent template. For example:

```html
{% set_resources(css_files='/ui/bootstrap/dist/bootstrap.min.css') %} <!-- add Bootstrap -->
{% set_resources(javascript_files='/ui/lodash/lodash.min.js') %}      <!-- add lodash -->
{% set_resources(embedded_css='th { padding: 4px; }') %}    <!-- add CSS -->
{% set_resources(embedded_js='alert("OK")') %}              <!-- add CSS -->
```

### Raw sub-templates

You can also include other files using `{{ gramex.cache.open(...) }}`. For example:

```html
{% raw gramex.cache.open('README.txt') %}   -- inserts README.txt in-place
{% raw gramex.cache.open('README.md') %}    -- inserts README.md as HTML
```

The second open statement converts README.md into HTML. See
[data caching](../caching/#data-caching) for more formats.


## XSRF

If you're submitting forms using the POST method, you need to submit an
[_xsrf][xsrf] field that has the value of the `_xsrf` cookie.

**When using HTML forms**, you can include it in the template using handlers'
built-in `xsrf_token` property:

```html
<form method="POST">
  <input type="hidden" name="_xsrf" value="{{ handler.xsrf_token }}">
</form>
```

To render a file as a template, use:

```yaml
url:
  template:
    pattern: /page                  # The URL /page
    handler: FileHandler            # displays a file
    kwargs:
      path: page.html               # named page.html
      template: true                # Render as a template
```

[xsrf]: http://www.tornadoweb.org/en/stable/guide/security.html#cross-site-request-forgery-protection

**When using AJAX**, no XSRF token is required (for modern browsers that send an
`X-Requested-With: XMLHttpRequest` header for AJAX.)

**When submitting from a server**, you need to retrieve an XSRF token first --
for example, by requesting it from a URL like `/xsrf` below:

```yaml
url:
  xsrf:
    pattern: /xsrf
    handler: FunctionHandler
    kwargs:
      function: handler.xsrf_token.decode('utf-8')  # Return the XSRF token
```

Then you can send the XSRF token:

1. As the `_xsrf` argument of the method (either in the URL or the body)
2. As the `X-Xsrftoken` or `X-Csrftoken` HTTP header

You can disable XSRF for a specific handler like this:

```yaml
url:
  name:
    pattern: ...              # When this page is visited,
    handler: ...              # no matter what the handler is,
    kwargs:
      ...
      xsrf_cookies: false   # Disable XSRF cookies
```

You can disable XSRF for *all handlers* like this (but this is **not recommended**):

```yaml
app:
  settings:
    xsrf_cookies: false
```

For debugging without XSRF, start Gramex with a `--settings.xsrf_cookies=false` from the command line.

The XSRF cookie is automatically set when a FileHandler [template](#templates)
accesses `handler.xsrf_token`. You can also set it explicitly, by adding a
`set_xsrf: true` configuration to `kwargs` like this:

```yaml
url:
  name:
    pattern: ...              # When this page is visited,
    handler: ...              # no matter what the handler is,
    kwargs:
      ...
      set_xsrf: true        # set the xsrf cookie
```

### How XSRF works

Tornado's XSRF:

- Sets a random non-expiring `_xsrf` cookie when
  `tornado.web.RequestHandler.xsrf_token()` is called. It is `httponly` by
  default in Gramex because of the default `xsrf_cookie_kwargs` setting, but not
  set to `secure` to allow HTTP sites to access it
- Checks if the `_xsrf` GET/POST argument (or the `X-Xsrftoken` or `C-Xsrftoken`
  headers) is a valid XSRF token, and checks that it matches the cookie value

## FileHandler HTTP methods

By default FileHandler supports `GET`, `HEAD` and `POST` methods. You can map
any of the following methods to the file using the `methods:` configuration as
follows:

```yaml
url:
  name:
    pattern: ...
    handler: FileHandler
    kwargs:
      ...
      methods: [GET, HEAD, POST, DELETE, PATCH, PUT, OPTIONS]
```

## File concatenation

You can concatenate multiple files and serve them as a single file. For example:

```yaml
    ...
    pattern: /libraries.js
    handler: FileHandler
    kwargs:
      path:
        - bower_components/jquery/dist/jquery.min.js
        - bower_components/bootstrap/dist/bootstrap.min.js
        - bower_components/d3/d3.v3.min.js
      headers:
        Cache-Control: public, max-age=86400    # Cache publicly for 1 day
```

This concatenates all files in `path` in sequence. If transforms are
specified, the transforms are applied before concatenation.

This is useful to pack multiple static files into one, as the example shows.


[filehandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.FileHandler
[template]: http://www.tornadoweb.org/en/stable/template.html
[template-syntax]: http://www.tornadoweb.org/en/stable/guide/templates.html#template-syntax


## Transforming content

Rather than render files as-is, the following parameters transform the markdown
into HTML:

```yaml
    # ... contd ...
      transform:
        "*.md":                                 # Any file matching .md
          function: markdown.markdown(content)  #   Convert .md to html
          kwargs:                               #   Pass these arguments to markdown.markdown
            output_format: html5                #     Output in HTML5
          headers:                              #   Use these HTTP headers:
            Content-Type: text/html             #     MIME type: text/html
```

Any `.md` file will be displayed as HTML -- including this file (which is [README.md](README.md.source).)

Any transformation is possible. For example, this configuration converts YAML
into HTML using the [BadgerFish](http://www.sklar.com/badgerfish/) convention.

```yaml
    # ... contd ...
        "*.yaml":                               # YAML files use BadgerFish
          function: badgerfish(content)         # transformed via gramex.transforms.badgerfish()
          headers:
            Content-Type: text/html             # and served as HTML
```

Using this, the following file [page.yaml](page.yaml) is rendered as HTML:

```yaml
    html:
      "@lang": en
      head:
        meta:
          - {"@charset": utf-8}
          - {"@name": viewport, "@content": "width=device-width, initial-scale=1.0"}
        title: Page title
        link: {"@rel": stylesheet, "@href": /style.css}
      body:
        h1: Page constructed using YAML
        p: This file was created as YAML and converted into HTML using the BadgerFish convention.
```

Transforms take the following keys:

- **function**: The function to call as `function(*args, **kwargs)` using the
  `args` and `kwargs` below. You can use `=content` for the content and
  `=handler` for the handler in both `args` and `kwargs`.
- **args**: Positional parameters to pass. Defaults to the file contents.
- **kwargs**: Keyword parameters to pass.
- **encoding**: If blank, the file is treated as binary. The transform
  `function` MUST accept the content as binary. If you specify an encoding, the
  file is loaded with that encoding.
- **headers**: HTTP headers for the response.

Any function can be used as a transform. Gramex provides the following (commonly
used) transforms:

1. **template**. Use `template: true` to render a template. See
   [Templates](#templates). But if you need to pass additional arguments to the
   template, use `function: template`. Any `kwargs` passed will be sent as
   variables to the template. For example:

```yaml
    transform:
        "template.*.html":
            function: template            # Convert as a Tornado template
            args: =content                # Using the contents of the file (default)
            kwargs:                       # Pass it the following parameters
                handler: =handler         # The handler variable is the RequestHandler
                title: Hello world        # The title variable is "Hello world"
                path: $YAMLPATH           # path is the current YAML file path
                home: $HOME               # home is the YAML variable HOME (blank if not defined)
                series: [a, b, c]         # series is a list of values
```

You can also write this as:

```yaml
    transform:
        "template.*.html":
            function: |
                template(content, handler=handler, title="Hello world", path="$YAMLPATH",
                            home="$HOME", series=["a", "b", "c"])
```

With this structure, the following template will render fine:

```yaml
<h1>{{ title }}</h1>
<p>argument x is {{ handler.get_argument('x', None) }}</p>
<p>path is: {{ path }}.</p>
<p>home is: {{ home }}.</p>
<ul>
    {% for item in [series] %}<li>{{ item }}</li>{% end %}
</ul>
```

2. **badgerfish**. Use `function: badgerfish(content)` to convert YAML files into
   HTML. For example, this YAML file is converted into a HTML as you would
   logically expect:

```yaml
    html:
        head:
        title: Sample file
        body:
        h1: Sample file
        p:
            - First paragraph
            - Second paragraph
```
