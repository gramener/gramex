---
title: Writing handlers
prefix: BaseHandler
...

[TOC]

Gramex handlers must inherit from [gramex.handlers.BaseHandler][basehandler]. Here's a simple custom handler saved in [handlerutil.py](handlerutil.py):

    :::python
    from gramex.handlers import BaseHandler

    class CustomHandler(BaseHandler):
        def get(self):
            self.write('This is a custom handler')

You can use this in `gramex.yaml` to map it to [custom](custom):

    :::yaml
    url:
        handler/custom:
            pattern: /$YAMLURL/custom
            handler: handlerutil.CustomHandler

Extending `BaseHandler` automatically provides these features:

- **Method overriding**. The `X-HTTP-Method-Override: PUT` HTTP header changes
  the request to a `PUT` request. If the URL has `?x-http-method-override=PUT`,
  it becomes a `PUT` request. Similarly for `GET`, `POST` or `DELETE`.
- [Authentication and authorization](../auth/) via the `auth:` settings
- [Error handling](../config/#error-handlers) via the `error:` settings
- [XSRF cookie flag](../filehandler/#xsrf) via the `xsrf_cookies:` and `set_xsrf:` settings
- [Caching](../cache/) via the `cache:` settings
- [Sessions](../auth/) via the `session:` settings
- Headers via the `headers:` settings for some handlers
- Transforms via the `transform:` settings for some handlers like
  [ProcessHandler](../processhandler/) and [FileHandler](../filehandler/)

**Note**: when naming your Python script, avoid namespaces such as `services.` or
`handlers.` -- these are already used by Gramex, and will not reflect your custom
handler.


## Initialisation

Any arguments passed to the handler are passed to the `setup()` and
`initialize()` methods. `setup()` is a class method that is called once.
`initialize()` is an instance method that is called every request. For example:

    :::python
    class SetupHandler(BaseHandler):
        @classmethod
        def setup(cls, **kwargs):                           # setup() is called
            super(SetupHandler, cls).setup(**kwargs)        # You MUST call the BaseHandler setup
            cls.name = kwargs.get('name', 'NA')             # Perform any one-time setup here
            cls.count = Counter()

        def initialize(self, **kwargs):                     # initialize() is called with the same kwargs
            super(SetupHandler, self).initialize(**kwargs)  # You MUST call the BaseHandler initialize
            self.count[self.name] += 1                      # Perform any recurring operations here

        def get(self):
            self.write('Name %s was called %d times' % (self.name, self.count[self.name]))

... can be initialised at [setup](setup) as follows:

    :::yaml
    url:
        handler/setup:
            pattern: /$YAMLURL/setup
            handler: handlerutil.SetupHandler
            kwargs:                     # This is passed to setup() and initialize() as **kwargs
                name: ABC


## BaseHandler Attributes

The following attributes are available to `BaseHandler` instances:

- `handler.name` (str): the name of the URL configuration section that created this handler
- `handler.conf` (AttrDict): the full configuration used to create the handler,
  parsed from YAML. For example, `handler.conf.pattern` has the `pattern:`
  section. `handler.conf.kwargs` has the handler kwargs.
- `handler.kwargs` (AttrDict): Same as `handler.conf.kwargs`. Retained for
  backward compatibility and convenience.
- `handler.args` (dict): a unicode dictonary of URL query parameters. Values are
  lists. For example, `?x=1` is passed as `handler.args = {'x': ['1']}`
- `handler.get_arg(key, default)` returns the last value of `handler.args[key]`
  if it exists - else returns default. If no default is specified, it raises a
  `tornado.web.MissingArgumentException`. Passing `first=True` returns the
  first value instead of the last.
- `handler.session` (AttrDict): a unique object associated with each [session](../auth/)

Apart from these, there are 4 other variables that may be created based on the
configuration. These are not yet intended for general use:

- `handler.transform`
- `handler.redirects`
- `handler.permissions`
- `handler.cache`

[basehandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.BaseHandler

## Tornado handler attributes

These attributes are available to all Gramex handlers via Tornado:

- `handler.request` (HTTPRequest): raw details of the HTTP request, such as:
    - `handler.request.method`: HTTP request method, e.g. "GET" or "POST"
    - `handler.request.uri`: The requested uri.
    - `handler.request.path`: The path portion of `uri`
    - `handler.request.query`: The query portion of `uri`
    - `handler.request.version`: HTTP version specified in request, e.g. "HTTP/1.1"
    - `handler.request.headers`: dict-like HTTP request headers
    - `handler.request.body`: Request body, if present, as a byte string.
    - `handler.request.remote_ip`: Client's IP address as a string. Uses `X-Real-Ip` or `X-Forwarded-For` header
    - `handler.request.protocol`: The protocol used, either "http" or "https"
    - `handler.request.host`: The requested hostname, usually taken from the ``Host`` header.
    - `handler.request.files`: dict-like file names mapped to `HTTPFile` class which has
        - `.filename`: uploaded file name
        - `.body`: file content as byte string
        - `.content_type`: file MIME type
    - `handler.request.cookies`: dict-like HTTP request cookies
- `handler.path_args` (tuple): the URL pattern position matches. For example,
  `url: /get/(\w+)/(\d+)` matches `/get/user/123`
  with `path_args` as `('user', '123')`.
- `handler.path_kwargs` (dict): the URL pattern named matches. For example,
  `url: /get/(?P<item>\w+)/(?P<id>\d+)` matches `/get/user/123`
  with `path_kwargs` as `{'item': 'user', 'id': '123'}`.
