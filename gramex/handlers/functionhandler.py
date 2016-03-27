import tornado.web
import tornado.gen
from .basehandler import BaseHandler
from ..transforms import build_transform


class FunctionHandler(BaseHandler):
    '''
    Renders the output of a function when the URL is called via GET or POST. It
    accepts these parameters when initialized:

    :arg string function: a string that resolves into any Python function or
        method (e.g. ``str.lower``). By default, it is called as
        ``function(handler)`` where handler is this RequestHandler, but you can
        override ``args`` and ``kwargs`` below to replace it with other
        parameters. The result is rendered as-is (and hence must be a string.)
        If ``redirect`` is specified, the result is discarded and the user is
        redirected to ``redirect``.
    :arg list args: positional arguments to be passed to the function.
    :arg dict kwargs: keyword arguments to be passed to the function.
    :arg dict headers: HTTP headers to set on the response.
    :arg string redirect: URL to redirect to when the result is done. Used to
        trigger calculations without displaying any output.

    Here's a simple use -- to display a string as a response to a URL. This
    configuration renders "Hello world" at the URL `/hello`::

        url:
          hello-world:
            pattern: /hello                             # The URL /hello
            handler: gramex.handlers.FunctionHandler    # Runs a function
            kwargs:
              function: str                             # Display string as-is
              args:
                - Hello world                           # with "Hello world"

    Only a single function call is allowed. To chain function calls or to do
    anything more complex, create a Python function and call that instead. For
    example, create a ``calculations.py`` with this method::

        import json
        def total(*items):
            'Calculate total of all items and render as JSON: value and string'
            total = sum(float(item) for item in items)
            return json.dumps({
                'display': '${:,.2f}'.format(total),
                'value': total,
            })

    Now, you can use this configuration::

        url:
          total:
            pattern: /total                             # The URL /total
            handler: gramex.handlers.FunctionHandler    # Runs a function
            kwargs:
              function: calculations.total              # calculations.total(100, 200.0)
              args: [100, 200.0]
              headers:
                Content-Type: application/json          # Returns the result as JSON

    ... to get this result in JSON::

        {"display": "$300.00", "value": 300.0}

    If no ``args`` is specified, the Tornado `RequestHandler`_ is passed as the
    only positional argument. For example, in ``calculations.py``, add::

        def add(handler):
            return str(sum(float(x) for x in handler.get_arguments('x')))

    .. _RequestHandler: http://tornado.readthedocs.org/en/stable/web.html#request-handlers

    Now, the following configuration::

        function: calculations.add

    ... takes the URL ``?x=1&x=2&x=3`` to add up 1, 2, 3 and display ``6.0``.

    You can pass the handler along with custom arguments. ``=handler`` is
    replaced by the RequestHandler. For example::

        url:
          method:
            pattern: /method                       # The URL /method
            handler: gramex.handlers.FunctionHandler    # Runs a function
            kwargs:
              function: calculations.method
              args:
                  - =handler          # This is replaced with the RequestHandler
                  - 10
              kwargs:
                  h: =handler         # This is replaced with the RequestHandler
                  val: 0

    ... calls ``calculations.method(handler, 10, h=handler, val=0)``.

    You can specify wildcards in the URL pattern. For example::

        url:
          lookup:
            pattern: /name/([a-z]+)/age/([0-9]+)        # e.g. /name/john/age/21
            handler: gramex.handlers.FunctionHandler    # Runs a function
            kwargs:
              function: calculations.name_age           # Run this function

    When you access ``/name/john/age/21``, ``john`` and ``21`` can be accessed
    via ``handler.path_args`` as follows::

        def name_age(handler):
            name = handler.path_args[0]
            age = handler.path_args[1]

    You can use asynchronous functions via Tornado's `Coroutines`_ like this::

        @tornado.gen.coroutine
        def fetch(url1, url2):
            client = tornado.httpclient.AsyncHTTPClient()
            r1, r2 = yield [client.fetch(url1), client.fetch(url2)]
            raise tornado.gen.Return(r1.body + r2.body)

    This `fetch` function can be used as a FunctionHandler.

    The simplest way to call a blocking function asynchronously is to use a
    ``ThreadPoolExecutor``::

        thread_pool = tornado.concurrent.ThreadPoolExecutor(4)

        @tornado.gen.coroutine
        def calculate(data1, data2):
            group1, group2 = yield [
                thread_pool.submit(data1.groupby, ['category']),
                thread_pool.submit(data2.groupby, ['category']),
            ]
            result = thead_pool.submit(pd.concat, [group1, group2])
            raise tornado.gen.Return(result)

    .. _Coroutines: http://tornado.readthedocs.org/en/stable/guide/coroutines.html

    To redirect to a different URL when the function is done, use ``redirect``::

        url:
          lookup:
            function: calculation.run     # Run calculation.run(handler)
            redirect: /                   # and redirect to / thereafter
    '''
    def initialize(self, **kwargs):
        self.params = kwargs
        self.function = build_transform(kwargs, vars={'handler': None})
        self.headers = kwargs.get('headers', {})
        self.redirect_url = kwargs.get('redirect', None)
        self.post = self.get

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self, *path_args):
        result = self.function(handler=self)
        for header_name, header_value in self.headers.items():
            self.set_header(header_name, header_value)
        if self.redirect_url is not None:
            self.redirect(self.redirect_url or self.request.headers.get('Referer', '/'))
        else:
            value = yield result
            self.write(value)
            self.flush()
