title: Writing handlers

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
- [Caching](../cache/) via the `cache:` settings
- [Sessions](../auth/) via the `session:` settings
- [Authentication and authorization](../auth/) via the `auth:` settings
- Transforms that are used by [ProcessHandler](../processhandler/) and [FileHandler](../filehandler/)

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