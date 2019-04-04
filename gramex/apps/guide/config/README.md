---
title: Configurations control Gramex
prefix: Config
...

[TOC]

All features of Gramex are controlled by `gramex.yaml`. Here's a simple
`gramex.yaml` that serves the file `home.html` as the home page.

```yaml
url:                            # URL configuration section
    root:                       # Add a configuration called "root"
        pattern: /              # It maps the URL / (the home page)...
        handler: FileHandler    # ... to a Gramex FileHandler
        kwargs:                 # ... and passes it these arguments:
            path: home.html     # Use home.html as the path to serve
app:
    browser: /                  # Open the home page when the app loads
```

Create this `home.html` in the same directory:

```html
<h1>Hello Gramex</h1>
```

Run `gramex` from that directory. You should see "Hello Gramex" on your browser.
(You may need to press `Ctrl+F5` or `Ctrl+R` to refresh the cache.

Here is a full [reference of gramex.yaml configurations](../root.gramex.yaml).

This section is meant more as a **reference**. Skim through it, and return later
for additional information.

## App configuration

The `app:` section controls Gramex's startup. It has these sub-sections.

1. `browser:` is the URL to open when Gramex is launched. (default: `False`)
2. `listen:` holds keyword arguments for the HTTP server. The most important
   parameter is the `port:` (default: 9988.) The remaining parameters are passed
   to [HTTPServer()](http://www.tornadoweb.org/en/stable/_modules/tornado/httpserver.html#HTTPServer).
3. `settings:` holds the Tornado
   [application settings](http://www.tornadoweb.org/en/stable/web.html#tornado.web.Application.settings).
4. `debug:` holds the [debug settings](../debug/)
5. `session:` holds [session settings](../auth/)

## Command line args

The app section alone can be over-ridden from the command line. (Other sections
cannot.) For example:

```bash
gramex --listen.port=8888 --settings.debug=True --browser=/
```

... will override the `gramex.yaml` parameters for the `port` and `browser`.
This is the same as specifying:

```yaml
app:
    listen:
        port: 8888
    settings:
        debug: True
    browser: '/'
```

## URL mapping

The `url:` section maps URLs to content. Here is an example:

```yaml
url:
    homepage:                           # "homepage" can be replaced with any unique name
        pattern: /                      # Map the URL /
        handler: FileHandler            # using a built-in FileHandler
        kwargs:                         # Pass these options to FileHandler
            path: $YAMLPATH/index.html  # Show the index.html in the same directory as this YAML file

    hello:                              # A unique name for this mapping
        pattern: /hello                 # Map the URL /hello
        handler: FunctionHandler        # using the build-in FunctionHandler
        kwargs:                         # Pass these options to FunctionHandler
            function: str("Hello")      # Run the str() function with the argument "Hello"
```

The `url:` section is a name - mapping dictionary. The names are just unique
identifiers. The mappings have these keys:

- `pattern`: a regular expression that matches the URL. For example,
  `/blog/(.*)` matches all pages starting with `/blog/`. Any parts of the URL in
  brackets are passed to the handler as arguments.
- `handler`: The name of the Tornado [RequestHandler][requesthandler] to run.
  Gramex provides many handlers by default. Here are some commonly used ones:
    - [FunctionHandler](../functionhandler/): runs any function and renders the output
    - [FileHandler](../filehandler/): transforms & displays files
    - [DataHandler](../datahandler/): renders data from databases or files
- `kwargs`: Keyword arguments to pass to the handler. The arguments varies by handler.
- `priority`: A number indicating the priority. By default, the mapping has a
  priority of 0. Use 1, 2, etc for higher priority, -1, -2, etc for lower
  priority. Mappings with a higher priority override those with lower priority.

You an write your own handler by extending [BaseHandler](../handlers/). For
example, create a file called `hello.py` with the following content:

```python
from gramex.handlers import BaseHandler

class Hello(BaseHandler):
    def get(self):
        self.write('hello world')
```

Now, you can add this configuration to your `url:` section:

```yaml
url:                # Do not include this line if you already have it
    hello:                        # a name you want to give to the handler
        pattern: /hello           # URL pattern
        handler: hello.Hello      # class that implements the handler
```

This renders "hello world" at the URL [/hello](hello).

[requesthandler]: http://tornado.readthedocs.org/en/latest/web.html#request-handlers

## Custom HTTP Headers

The `kwargs:` section of `url:` accepts a `headers:` key that sets custom HTTP
headers. For example:

```yaml
pattern: /custom-header
handler: ...
kwargs:
    ...
    headers:
        Content-Type: text/plain          # Display as plain text
        Access-Control-Allow-Origin: '*'  # Allow CORS (all servers can access via AJAX)
```

... adds the Content-Type and CORS settings to the response headers.


## Logging

The `log:` section defines Gramex's logging behaviour. See
[gramex.yaml][gramex-yaml] for the default configuration.

To only log WARNING messages to the console, use:

```yaml
log:
    root:
        level: WARNING      # Default: DEBUG. Can be INFO, WARNING, ERROR
```

From **v1.23**, Gramex also saves all console logs to `logs/gramex.log` under
[$GRAMEXDATA](#predefined-variables). To change the path, use:

```yaml
log:
    handlers:
        logfile:
            filename: $GRAMEXDATA/your-app/gramex.log       # Change file location
```

The log file is backed up weekly by default. You can change these [parameters][trfh]:

- `filename`: defaults to `$GRAMEXDATA/logs/gramex.log`
- `when`: can be `s`, `m`, `h`, `d`, `w0` to `w6` or `midnight`. See [TimedRotatingFileHandler][trfh]. Defaults to `w0`, i.e. Monday
- `interval`: for example, if this is 6 and `when: h`, the log file is rotated every 6 hours.  Defaults to 1, i.e. every Monday
- `backupCount`: number of backups to retain. Defaults to 52, i.e. 52 weeks of backup
- `encoding`: defaults to `utf-8`
- `utc`: set to `true` to use UTC. Defaults to `false` (i.e. local time)

The [default configuration][gramex-yaml] uses the [Python logging schema][logging-schema].
You can create your additional formatters by extending this.

[logging-schema]: https://docs.python.org/3/library/logging.config.html#dictionary-schema-details
[trfh]: https://docs.python.org/3/library/logging.handlers.html#logging.handlers.TimedRotatingFileHandler
[gramex-yaml]: https://github.com/gramener/gramex/blob/master/gramex/gramex.yaml

### Request logging

Gramex logs all HTTP requests to `logs/requests.csv` under [$GRAMEXDATA](#predefined-variables).
It logs:

- `time`: Time of the request in milliseconds since epoch
- `ip`: The IP address of the client requesting the page
- `user.id`: The unique ID of the user requesting the page
- `status`: The HTTP status code of the response (e.g. 200, 500)
- `duration`: Time taken to serve the request in milliseconds
- `method`: The HTTP method requested (e.g. GET or POST)
- `uri`: The full URL requested (after the host name)
- `error`: Any error raised while processing the request

To change the location of this file, use `log.handlers.requests.filename`:

```yaml
log:
    handlers:
        requests:
            filename: $GRAMEXDATA/your-app/requests.csv      # The path can point ANYWHERE
```

To change the columns that are logged, use `log.handlers.requests.keys:`

```yaml
log:
    handlers:
        requests:
            keys: [time, ip, user.email, status, uri]
```

You can use any of the following as keys for logging:

- `time`: Time of the request in milliseconds since epoch
- `datetime`: Time in UTC as YYYY-MM-DD HH:MM:SSZ
- `name`: Handler name (the key in gramex.yaml)
- `class`: Handler class (e.g. FormHandler)
- `ip`: The IP address of the client requesting the page
- `user`: The unique ID of the user requesting the page (same as `user.id`)
- `status`: The HTTP status code of the response (e.g. 200, 500)
- `duration`: Time taken to serve the request in milliseconds
- `port`: HTTP port on which Gramex is running
- `method`: The HTTP method requested (e.g. GET or POST)
- `uri`: The full URL requested (after the host name)
- `error`: Any error raised while processing the request
- `session`: The unique session ID object
- `args.<key>`: A specific argument. E.g. `args.x` returns the value of `?x=...`
- `headers.<key>`: A request HTTP header. E.g. `headers.User-Agent` is the browser's user agent
- `session.<key>`: A HTTP session key. E.g. `session.user` is the user object
- `cookies.<key>`: Logs a specific cookie. E.g. `cookie.sid` is the session ID cookie
- `env.<key>`: Logs an environment variable. E.g. `env.HOME` logs the user's home directory

### User logging

Gramex's [auth handlers](../auth/) log all login and logout events to
`logs/user.csv` under [$GRAMEXDATA](../config/#predefined-variables). It logs:

- `datetime`: Time in UTC as YYYY-MM-DD HH:MM:SSZ
- `event`: "login" or "logout"
- `session`: session ID that the user was logged into
- `user`: The ID of the user
- `ip`: The IP address of the client requesting the page
- `headers.User-Agent`: The User-Agent (browser) that accessed the page

To change the location of this file, use `log.handlers.user.filename`:

```yaml
log:
    handlers:
        user:
            filename: $GRAMEXDATA/your-app/user.csv     # The path can point ANYWHERE
```

To change the columns that are logged, use `log.handlers.user.keys:`

```yaml
log:
    handlers:
        user:
            keys: [time, ip, user, status, uri, error]
```

For the list of valid keys, see [request logging](#request-logging).

--------

Until **v1.22**, the `log:` section of auth handlers  could be configured to
log events like this:

```yaml
auth:
    pattern: /$YAMLURL/auth
    handler: SimpleAuth
    kwargs:
        log:                                # Log this when a user logs in via this handler
            fields:                         # List of fields:
                - session.id                  #   handler.session['id']
                - current_user.id             #   handler.current_user['id']
                - request.remote_ip           #   handler.request.remote_ip
                - request.headers.User-Agent  #   handler.request.headers['User-Agent']
```

The `log:` key has been **removed since v1.23**.


### Handler logging

Up to Gramex **v1.22** the `log:` section of each handler allowed custom logging
for that handler. This is useless sophistication. It has not been used in any
Gramener project. So it was removed in **v1.23**.

Instead, use [request logging](#request-logging) to set up access logs.

Logging to `$GRAMEXDATA/logs/access.csv` has also been disabled since no project
uses it by default.


## Error handlers

URL handlers allow custom logging of errors. For example, to show a custom 404 page, use:

```yaml
url:
    pattern: ...
    handler: ...
    kwargs:
        ...
        error:
            404:
                path: $YAMLPATH/error-page.html
```

Here is an example of an [error-page](error-page). The error page is rendered as
a Tornado template with 3 keyword arguments:

- `status_code`: the HTTP status code of the error
- `kwargs`: if this error was caused by an uncaught exception or raising a
  HTTPError, `kwargs['exc_info']` is available as an exception triple
- `handler`: the handler object

The error page can also be a function. For example:

```yaml
url:
    pattern: ...
    handler: ...
    kwargs:
        ...
        error:
            500:
                function: config_error_page.show_error
```

The function is passed the same 3 keyword arguments mentioned above. Its return
value is rendered as a string.

If a `function:` **and** `path:` are both specified, `function:` is used, and
`path:` is ignored with a warning log.

To repeat error pages across multiple handlers, see [Reusing Configurations](#reusing-configurations).

Both methods support some customisations. Here is a full example showing the
customisations:

```yaml
url:
    pattern: ...
    handler: ...
    kwargs:
        ...
        error:
            404:
                path: $YAMLPATH/error-page.json   # Content-Type is set to application/json based on extension
                autoescape: false         # To avoid converting quotes to &quot; etc
                whitespace: oneline       # Remove all whitespace. 'single' preserves newlines. 'all' preserves all whitespace
                headers:                  # Override HTTP headers
                    Content-Type: text/plain
            500:
                # Call your function errors.show with the predefined parameters available
                function: errors.show(status_code, kwargs, handler)
                headers:                                  # Override HTTP headers
                    Cache-Control: no-cache
```

## Redirection

Most URL handlers (not all) accept a `redirect:` parameter that redirects the
user after completing the action. For example, after a
[FunctionHandler](../functionhandler/) executes or after
[logging in](../auth/) or after an
[UploadHandler](../uploadhandler/) is done. Here is the syntax:

```yaml
url:
    pattern: ...
    handler: ...
    kwargs:
        ...
        # Redirect the browser to this path after execution
        redirect: /$YAMLURL/path-to-redirect
        # You can also specify an absolute path, e.g.
        # redirect: /home
        # ... or a relative path, e.g.
        # redirect: ../css/style.css
```

**NOTE**: You can only redirect pages that don't return any content. If the
handler renders content or triggers a download, redirection will fail.

Redirection can also be customised based on:

- a URL `query` parameter
- a HTTP `header`, or
- a direct `url`

These can be specified in any order, and are all optional. (If none of these is
specified, the user is redirected to the home page `/`.) For example:

```yaml
    kwargs:
        ...
        redirect:             # Redirect options are applied in order
        query: next         # If ?next= is specified, use it
        header: Referer     # Else use the HTTP header Referer if it exists
        url: /$YAMLURL/     # Else redirect to the directory where this gramex.yaml is present
```

With this configuration, `?next=../config/` will take you to the `../config/`
page.

By default, the URL must redirect to the same server (for security reasons). So
`?next=https://some-other-domain.com/` will ignore the `next=` parameter.
However, you can specify `external: true` to override this:

    ::yaml
        kwargs:
          ...
          redirect:                     # Under the redirect section,
              external: true            # add an external: true
              query: next               # The ?next= can now be an external URL
              url: http://example.com/  # So can the pre-defined URL

You can test this at
[../auth/ldap2?next=https://gramener.com/](../auth/ldap2?next=https://gramener.com/).


## Scheduling

The `schedule:` section schedules functions to run at specific times or on
startup. It has a name - schedule mapping. The names are unique identifiers. The
schedules have the following keys:

- `function:` name of the function or expression to run. (If `function:` is the
  function name, you can optionally add `args:` and `kwargs:`)
- `startup`: True to run the function on startup (default: False)

It also accepts a timing that is based on the [crontab format][crontab]. Here is
an example:

- `years`: 2016-2019            # From year 2016 - 2019
- `months`: 'jan, mar-may, 12'  # In Jan, Mar, Apr, May, Dec
- `dates`: '1, L'               # On the first and last days
- `weekdays`: '*'               # 0-6 or SUN-SAT
- `hours`: '*/3'                # Every 3rd hour
- `minutes`: '*/5, 59'          # Every 5th minute, and 59th minute

See the [scheduler](../scheduler/) documentation for examples.

[crontab]: https://en.wikipedia.org/wiki/Cron#Format

## Custom MIME types

The `mime:` section lets you add custom MIME types for extensions. For example:

```yaml
mime:
    .yml: text/yaml
```

... maps the `.yml` extension to the `text/yaml` MIME type. This is used by
[FileHandler](../filehandler/) and other services to set the `Content-Type`
header.


## YAML imports

One config file can import another. For example:

```yaml
import: another.yaml        # import this YAML file relative to current file path
```

These "copy-paste" the contents of `another.yaml` from the same directory as
this file, ignoring any duplicates.

To import multiple files, path can be a list or a wildcard. For example:

```yaml
import:
  app:
    path:
        - another.yaml          # Relative paths are relative to this YAML file
        - D:/temp/gramex.yaml   # Absolute paths are OK too
        - '*/gramex.yaml'       # Any gramex.yaml file under an immediate sub-directory
        - '**/gramex.yaml'      # Any gramex.yaml file under ANY sub-directory
    namespace: [url, schedule, cache, import]
```

You can pass variables to the imported file using this syntax:

```yaml
import:
  app:
    path: another.yaml
    var1: value               # $var1 will be replaced with "value"
    var2: {key: value}        # $var2 will be replaced with {"key": "value"}
```

The `$YAMLURL` and `$YAMLPATH` [variables](#yaml-variables) work as expected. But
you may change `$YAMLURL` to mount an import at a different URL. Consider this
`dir/app.yaml`:

```yaml
url:
    myroot:
        pattern: /$YAMLURL/
        ...
```

When imported using `import: dir/app.yaml`, `$YAMLURL` becomes `/dir/`. But you
may want to mount applications in different locations, so you can change the
imported file's `$YAMLURL` as follows:

```yaml
import:
    app1:
        path: dir/app.yaml          # YAMLURL is /dir/ by default
        YAMLURL: /app1/             # YAMLURL is not set to /app1/ instead
        # Here are some other options
        # YAMLURL: $YAMLURL         # pattern is $YAMLURL, as if dir/app.yaml were copy-pasted here
        # YAMLURL: /app/dir/        # pattern is /app/dir/
    app2:
        path: dir/app2.yaml         # Another application
        YAMLURL: /app2/             # is mounted at /app2/
```

The keys `app1`, `app2`, etc. are just identifiers, not used for anything.

You can also use imports within sections. For example:

```yaml
url:
    import: app1/gramex.yaml  # Imports app1/gramex.yaml into the url: section
```

**Notes**

- Using `$YAMLPATH` for import: is optional. By default, imports are relative to
  the YAML file.
- If a file is missing, Gramex proceeds with a warning.
- UNIX shell style wildcards work. `*` matches anything, and `**` matches all
  subdirectories.
- Imports work recursively. You can have imports within imports.
- Avoid direct import of multiple files without namespaces. Examples are below.

```yaml
# BAD
import: '*/gramex.yaml'
# GOOD
import:
  app:
    path: '*/gramex.yaml'
    namespace: [url, schedule, cache, import]
```

## YAML duplicate keys

Sometimes, you want to use the same keys. For example, you may want to import
the same YAML file multiple times, but with different variables.

There are 2 ways of doing this: namespaces and wildcard keys.

### YAML namespaces

When importing another application, use namespaces like this:

```yaml
import:
  app:                          # Some unique name for the app
    path: another.yaml          # Relative paths are relative to this YAML file
    namespace: [url, schedule, cache, import]
```

The `namespace:` replaces the keys under `url:`, `schedule:`, `cache:` and
`import:` with a unique prefix, ensuring that these sections are merged without
conflict.

### YAML wildcard keys

When building an application for re-use, use wildcard keys like this:

```yaml
url:
    my-app-$*:                  # Note the '$*' in the key
        pattern: ...
```

Every `'$*'` in a key is replaced with a random string every time the file is
loaded -- ensuring that it is unique.


## YAML variables

Templates can use variables. Variables are written as `$VARIABLE` or
`${VARIABLE}`. All environment variables are available as variables by default.
For example:

```yaml
import: $HOME/gramex.yaml       # imports gramex.yaml from your home directory
```

You can define or override variables using the `variables:` section like this:

```yaml
variables:
    URLROOT: "/site"                  # Define $URLROOT
    HOME: {default: "/home"}          # Define $HOME if not defined earlier
    PATH: $URLROOT/path               # Define $PATH based on $URLROOT
```

`$URLROOT` is set to `/site`. If the variable was defined earlier in another
YAML file or the environment, that value is lost.

`$HOME` is set to `/home` *only if* it was not already defined. It *defaults* to
home, but does not override a previous value.

`$PATH` is set to `/site/path`. Its value is based on the previously defined
`$URLROOT`.

Variables can be of any type. For example:

```yaml
variables:
    NUMBER: 10
    BOOLEAN: false
```

They are substituted as-is if the variable is used directly. If it's part of a
string substitution, then it is converted into a string. For example:

```yaml
number: $NUMBER             # This is the int 10
number: /$NUMBER            # This is the string "/10"
mix: a-${BOOLEAN}-b         # This is the string "a-False-b"
```

### Predefined variables

In addition to environment variables, the following pre-defined variables are
available in every YAML file. (The examples assume you are processing
`D:/app/config/gramex.yaml`, and running Gramex from `D:/app/`):

- `$YAMLFILE`: absolute path to the current YAML file, e.g. `D:/app/config/gramex.yaml`
- `$YAMLPATH`: absolute directory of the current YAML file, e.g. `D:/app/config/`
- `$YAMLURL`: is the relative URL path to the directory of the current YAML file
  (without leading / trailing slashes) from the current working directory. e.g.
  `base/dir/gramex.yaml` has a `$YAMLURL` of `base/dir`, and `gramex.yaml` has a
  `$YAMLURL` of `.`.
- `$GRAMEXPATH`: absolute path to the Gramex directory
- `$GRAMEXAPPS`: absolute path to the Gramex apps directory
- `$GRAMEXHOST`: hostname of the system where Gramex is running
- `$GRAMEXDATA` is the directory where local Gramex data is stored. This is at:
    - `%LOCALAPPDATA%\Gramex Data\` on Windows
    - `~/.config/gramexdata/` on Linux
    - `~/Library/Application Support/Gramex Data/` on OS X

You can also access these from Python modules:

```python
from gramex.config import variables
variables['GRAMEXPATH']     # Same as $GRAMEXPATH
variables['GRAMEXDATA']     # Same as $GRAMEXDATA
```

### Computed variables

Variables can also be computed. For example, this runs `utils.get_root` to
assign `$URLROOT`:

```yaml
variables:
    URLROOT:
        function: utils.get_root
```

By default, the function is called with the variable name as key, i.e.
`utils.get_root(key='URLROOT')`. But you can specify any arguments. For example,
this calls `utils.get_root('URLROOT', 'test', x=1)`:

```yaml
variables:
    URLROOT:
        function: utils.get_root(key, 'test', x=1)
```

This is another way of doing the same thing:

```yaml
variables:
    URLROOT:
        function: utils.get_root
        args: [=key, 'test']
        kwargs: {x: 1}
```

Computed variables can also use defaults. For example, this assigns `get_home()`
to `$HOME` only if it's not already defined.

```yaml
variables:
    HOME:
        default:
            function: utils.get_home()
```

Note: As of now, the `function:` cannot use variables like `$HOME`, but can use
`gramex.config.variables['HOME']` instead.

Once the variables are assigned, the `variables` section is removed.

To learn about pre-defined variables, and how these variables are used in
practice, read [deployment patterns](../deploy/).

### Conditional variables

You can set variables based on a conditional expression. For example, this sets
`$PORT` based on `$OS`:

```yaml
variables:
    PORT:
        function: 4444 if "$OS".lower() is 'windows' else 8888
```

### Merging variables

To use scalar variables, just use `$VARIABLE`. But if you want merge a mapping,
use `import.merge: $VARIABLE`.

Here's how it works. In the code below, the `first:` and `second:` are identical.

```yaml
variables:
    var:                    # Defines $var
        key: value
first:
    key: default-value      # If no $var is defined, use this key
    import.merge: $var      # If it's defined, just merge the $var here, overriding key:
second:                     # The result of first: is the same as second:
    key: value
```

A practical use is when write apps. If you write a FormHandler that will be
imported by a project:

```yaml
url:
    app-data-$*:                    # FYI: $* avoids namespace clash when importing
        pattern: /$YAMLURL/data
        handler: FormHandler
        kwargs:
            ...
            query:
                # By default, these are the queries available
                sales: SELECT * FROM sales
                cost: SELECT * FROM cost
                # But you can allow the importing app to over-ride these queries
                import.merge: $queries
```

... then the project can import your app and override the queries like this:

```yaml
import:
    app:
        path: /path/to/app/gramex.yaml
        # The section below is passed to the app as $queries
        # It replaces the sales: and cost: in the app
        queries:
            sales: SELECT * FROM sales WHERE product='Laptop'
            cost: SELECT * FROM cost WHERE product='Laptop'
```

## Conditions

**v1.23**.
Any YAML dictionary like `key if condition: val` is replaced with `key: val` if
`condition` is True, and removed otherwise.

For example, this sets up different authentications on Windows vs non-Windows:

```yaml
auth if 'win' in sys.platform:
    pattern: /login
    handler: IntegratedAuth
auth if 'win' not in sys.platform:
    pattern: /login
    handler: LDAPAuth
```

If ` if ` is present in any key, the portion after `if` is evaluated as a Python
expression. All [YAML variables](#yaml-variables) and common modules (`re`,
`os`, `sys`, `datetime`, `socket`, `six`) are available to the expression.

Here are useful examples of conditions:

```yaml
# If Gramex is installed in a certain location, e.g. C:
key if 'C:' in GRAMEXPATH`: value

# If Gramex is running on a certain platform, e.g. win32, linux, cygwin, darwin
key if 'win' in sys.platform: value

# If Gramex is running on a specific server, e.g. uat.gramener.com:
key if 'uat' in socket.gethostname(): value

# If Gramex was started with a specific command line, e.g. --listen.port=8001
key if '--listen.port=8001' in ''.join(sys.argv[1:]): value

# If Gramex is running from a specific location, e.g. /tmp/
key if '/tmp/' in os.getcwd(): value

# If Gramex was started at a specific time, e.g. on Sunday (7)
key if datetime.date.today().weekday() == 7: value
```


## YAML inheritence

Configurations can be overwritten. For example:

```yaml
a: 1          # This is defined first
a: 2          # ... but this overrides it
```

will only use the second line.

Imports over-write the entire key. For example, if `a.yaml` has:

```yaml
key:
    x: 1
    y: 2
import: b.yaml
```

... and `b.yaml` has:

```yaml
key:
    z: 3
```

... the final `key` will only have `z: 3`.

Gramex uses 3 different configuration files. The first is Gramex's own
`gramex.yaml`. The second is the application's. The third is the command line.
These *update* keys, rather than overwriting them. For example, Gramex's
`gramex.yaml` has the following `url:` section:

```yaml
url:
    default:
        pattern: /(.*)
        ...
```

When your `gramex.yaml` uses a `url:` section like this:

```yaml
url:
    homepage:
        pattern: /
        ...
```

... the final URL section will have both the `default` and the `homepage` keys.
If the application uses the same key as Gramex's `gramex.yaml`, the latter will
be overwritten.

## Configuration access

Configurations are available in `gramex.conf`. For example, this will print the
computed value of applications port:

```python
import gramex
print(gramex.conf.app.listen.port)
```

`gramex.conf` is meant for reading. Do not change its value.

You can see this applications `gramex.conf` at [../final-config](../final-config)

If the underlying YAML files change, then `gramex.init()` is automatically
reloaded and all services are re-initialized.

## Reusing configurations

Sometimes, you need to re-use the same configurations multiple times. YAML's
[anchors][anchors] support this. For example, this is how you re-use
authentication:

```yaml
url1:
    pattern: ...
    handler: ...
    kwargs: ...
        auth: &GRAMENER_AUTH          # Define a variable called GRAMENER_AUTH
            membership:               # Whatever is under auth: is copied into GRAMENER_AUTH
                hd: [gramener.com]
url2:
    pattern: ...
    handler: ...
    kwargs: ...
        auth: *GRAMENER_AUTH          # Use the variable GRAMENER_AUTH
        # This is the same as copy-pasting the earlier auth: section here
        # auth:
        #     membership:
        #         hd: [gramener.com]
```

This is how you re-use error page definitions:

```yaml
url1:
    pattern: ...
    handler: ...
    kwargs:
        ...
        error: &DASHBOARD_ERROR      # Define a reference called DASHBOARD_ERROR
            404: {path: $YAMLPATH/error-page.html}
            500: {function: config_error_page.show_error}
url2:
    pattern: ...
    handler: ...
    kwargs:
        ...
        error: *DASHBOARD_ERROR       # Reuse DASHBOARD_ERROR reference
```

You can also re-use parts of a configuration. Place any configuration you want in
the `variables:` section. Then use `<<: *reference` to copy-paste it where you
need.

For example, if you need to re-use common headers, do this:

```yaml
variables:
    # Define any YAML configuration in the variables: section
    headers: &commonheaders
        Server: False
        X-XSS-Protection: '1'
        X-Frame-Options: SAMEORIGIN
        ...

url:
    pattern: ...
    handler: ...
        kwargs:
            ...
            headers:
                Content-Type: text/plain
                <<: *commonheaders          # Copy-paste this reference
```

You can use `<<: *commonheaders` in multiple URL patterns

[anchors]: http://camel.readthedocs.io/en/latest/yamlref.html#anchors

## YAML styling

YAML supports multi-line strings. You can wrap text like this:

```yaml
query: >
    SELECT group, SUM(*) FROM table
    WHERE column > value
    GROUP BY group
    ORDER BY group DESC
```

This is more readable than:

```yaml
query: SELECT group, SUM(*) FROM table WHERE column > value GROUP BY group ORDER BY group DESC
```

## Dynamic configuration

Gramex can re-configure itself dynamically from a YAML file or from a data structure.

Gramex loads configurations from 3 sources by default:

1. `source`: `gramex.yaml` from `$GRAMEXPATH` - the default Gramex configuration
2. `base`: `gramex.yaml` from the current directory
3. `cmd`: [Command line arguments](#command-line-args)

You can write a Python function to extend or modify this configuration by calling
`gramex.init()`. For example:

```python
gramex.init(
    app1=pathlib.Path('/app1/gramex.yaml'),
    app2=AttrDict(
        url=AttrDict(
            app2=AttrDict(
                pattern='/app2',
                handler='FileHandler',
                kwargs=AttrDict(path='/home/app2/index.html'),
            )
        )
    )
)
```

This adds 2 apps:

- `app1` loads the configuration from `app1/gramex.yaml` and is refreshed
  whenever the file changes.
- `app2` loads the configuration provided. It is refreshed when `gramex.init()`
  is called again with `app2=` as a parameter. Calls without an `app2=`
  parameter do not affect the `app2` configuration.

## Config Viewer

[`configview/`](configview/) shows `gramex` configuration as an explorable UI

To use it, add this to your gramex.yaml:

```yaml
import:
  configviewer:
    path: $GRAMEXAPPS/configeditor/gramex.yaml
    YAMLURL: /$YAMLURL/configview/
```

Now [`configview/`](configview/) has a configuration viewer.

To embed the viewer in a page, include this in your HTML:

```html
<link rel="stylesheet" href="configview/node_modules/jsoneditor/dist/jsoneditor.min.css">
<script src="configview/ui/jquery/dist/jquery.min.js"></script>
<script src="configview/node_modules/jsoneditor/dist/jsoneditor.min.js"></script>

<script src="configview/app.js"
    data-id="myeditor"
    data-url="configview/config/"
    data-style="height:600px;"></script>
```

This script adds JSON editor UI from `configview/config/` URL to `<div id="myeditor"></div>`.
 If `data-id` is missing, `editor` ID is created. Use `data-style` to set in-line styles.

<link rel="stylesheet" href="configview/node_modules/jsoneditor/dist/jsoneditor.min.css">
<script src="configview/ui/jquery/dist/jquery.min.js"></script>
<script src="configview/node_modules/jsoneditor/dist/jsoneditor.min.js"></script>
<script src="configview/app.js"
    data-id="myeditor"
    data-url="configview/config/"
    data-style="height:600px;"></script>

To `get` the modified configuration from UI.

```javascript
var editor = document.getElementById('myeditor').editor
var conf = editor.get()
```

TODO: Re-configure gramex config via UI.
<!---
var conf = document.getElementById('myeditor').editor.get()
$.ajax('configview/config/post?_xsrf='+_xsrf, {
  method: 'POST',
  data: {'data': JSON.stringify(conf)}
})
--->
