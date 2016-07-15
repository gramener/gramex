title: Gramex runs Python functions

The [FunctionHandler][functionhandler] runs a function and displays the output.
For example, this configuration maps the URL [total](total) to a
FunctionHandler:

    :::yaml
    url:
        total:
            pattern: total                              # The "total" URL
            handler: FunctionHandler                    # runs a function
            kwargs:
                function: calculations.total            # total() from calculations.py
                args: [100, 200.0, 300.00]              # It always gets 100, 200, 300
                headers:
                    Content-Type: application/json      # Display as JSON

It runs `calculations.total()` with the arguments `100, 200, 300` and returns
the result as `application/json`. [calculations.py](calculations.py) defines
`total` as below:

    :::python
    def total(*items):
        return json.dumps(sum(float(item) for item in items))

You can see all configurations used in this page in [gramex.yaml](gramex.yaml):

<iframe frameborder="0" src="gramex.yaml"></iframe>

## Function arguments

You can define what parameters to pass to the function. By default, the Tornado
[RequestHandler][requesthandler] is passed. The [add](add) URL takes the
handler and sums up numbers you specify. [add?x=1&x=2](add?x=1&x=2) shows 3.0.
Try it below:

<form action="add">
  <div><input name="x" value="10"></div>
  <div><input name="x" value="20"></div>
  <button type="submit">Add</button>
</form>

To set this up, [gramex.yaml](gramex.yaml) used the following configuration:

    :::yaml
    url:
        add:
            pattern: add                                # The "add" URL
            handler: FunctionHandler                    # runs a function
            kwargs:
                function: calculations.add              # add() from calculations.py
                headers:
                    Content-Type: application/json      # Display as JSON
  
[calculations.add(handler)](calculations.py) is called with the Tornado
[RequestHandler][requesthandler]. It accesses `handler.get_arguments('x')` to
add up all `x` arguments.

You can specify wildcards in the URL pattern. For example:

    :::yaml
    url:
      lookup:
        pattern: /name/([a-z]+)/age/([0-9]+)        # e.g. /name/john/age/21
        handler: FunctionHandler                    # Runs a function
        kwargs:
            function: calculations.name_age         # Run this function

When you access `/name/john/age/21`, `john` and `21` can be accessed
via `handler.path_args` as follows:

    :::python
    def name_age(handler):
        name = handler.path_args[0]
        age = handler.path_args[1]

You can pass any options you want to functions. For example, to call
`calculations.method(handler, 10, h=handler, val=0)`, you can use:

    :::yaml
    url:
      method:
        pattern: /method          # The URL /method
        handler: FunctionHandler  # Runs a function
        kwargs:
          function: calculations.method
          args:
              - =handler          # This is replaced with the RequestHandler
              - 10
          kwargs:
              h: =handler         # This is replaced with the RequestHandler
              val: 0

## Streaming output

If you perform slow calculations and want to flush interim calculations out to
the browser, use `yield`. For example, [slow?x=1&x=2&x=3](slow?x=1&x=2&x=3) uses
the function below to print the values 1, 2, 3 as soon as they are "calculated".
(You won't see the effect on learn.gramener.com. Try it on your machine.)

    :::python
    def slow_print(handler):
        for value in handler.get_arguments('x'):
            time.sleep(1)
            yield 'Calculated: %s\n' % value

When a function yields a string value, it will be displayed immediately. The
function can also yield a Future, which will be displayed as soon as it is
resolved. (Yielded Futures will be rendered in the same order as they are
yielded.)

## Asynchronous functions

If you are using an asynchronous Tornado function, like
[AsyncHTTPClient][asynchttpclient], they will not block the server. The function
runs in parallel while Gramex continues. When the function ends, the code
resumes. Use [coroutines][coroutines] to achieve this. For example, this fetches
a URL's body without blocking:

    :::python
    async_http_client = tornado.httpclient.AsyncHTTPClient()

    @tornado.gen.coroutine
    def fetch_body(url):
        'A co-routine that fetches the URL and returns the URL body'
        result = yield async_http_client.fetch(url)
        raise tornado.gen.Return(result.body)

You can combine this with the `yield` statement to fetch
mutiple URLs asynchronously, and display them as soon as the results are
available, in order:

    :::python
    def urls(handler):
        for delay in handler.get_arguments('x'):
            futures = [fetch_body('https://httpbin.org/delay/%s' % x) for x in handler.get_arguments('x')]
            for future in futures:
                yield future

See the output at [fetch?x=0&x=1&x=2](fetch?x=0&x=1&x=2).

The simplest way to call *any blocking function* asynchronously is to use a
[ThreadPoolExecutor][ThreadPoolExecutor]. For example, usng this code in a
`FunctionHandler` will run `slow_calculation` in a separate thread without
blocking Gramex. Gramex provides a global threadpool that you can use. It's at
`gramex.service.threadpool`.

    :::python
    result = yield gramex.service.threadpool.submit(slow_calculation, *args, **kwargs)

[ThreadPoolExecutor]: https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor

You can run execute multiple steps in parallel and consolidate their result as
well. For example:

    :::python
    @tornado.gen.coroutine
    def calculate(data1, data2):
        group1, group2 = yield [
            gramex.service.threadpool.submit(data1.groupby, ['category']),
            gramex.service.threadpool.submit(data2.groupby, ['category']),
        ]
        result = gramex.service.threadpool.submit(pd.concat, [group1, group2])
        raise tornado.gen.Return(result)

## Redirection

To redirect to a different URL when the function is done, use `redirect`:

    :::yaml
    url:
      lookup:
        function: calculation.run     # Run calculation.run(handler)
        redirect: /                   # and redirect to / thereafter

Note: Using `redirect: ""` redirects to referrer.

If you want the function to dynamally redirect to a URL, use
`handler.set_header()`:

    :::python
    def run(handler):
        handler.set_header('Location', '/url-to-redirect-to')
        return ''


[requesthandler]: https://tornado.readthedocs.org/en/stable/web.html#request-handlers
[asynchttpclient]: https://tornado.readthedocs.org/en/latest/httpclient.html#tornado.httpclient.AsyncHTTPClient
[functionhandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.FunctionHandler
[coroutines]: https://tornado.readthedocs.org/en/latest/guide/coroutines.html
