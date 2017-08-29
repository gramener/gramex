import time
import json
import tornado


def total(*items):
    '''Calculate total of all items and render as JSON: value and string'''
    return json.dumps(sum(float(item) for item in items))


def add(handler):
    '''Add all values of ?x= and display the result as a string'''
    args = handler.argparse(x={'nargs': '*', 'type': float})
    return json.dumps(sum(args.x))


def slow(handler):
    '''Show values of ?x=1 with a 1-second delay'''
    args = handler.argparse(x={'nargs': '*'})
    for value in args.x:
        time.sleep(1)
        yield 'Calculated: %s\n' % value


async_http_client = tornado.httpclient.AsyncHTTPClient()


@tornado.gen.coroutine
def fetch_body(url):
    '''Fetches the body of a URL. As a coroutine, this returns a Future'''
    result = yield async_http_client.fetch(url)
    raise tornado.gen.Return(result.body)


def fetch(handler):
    '''Yields a series of Futures that resolve to httpbin URLs'''
    args = handler.argparse(x={'nargs': '*'})
    # Initiate the requests
    futures = [fetch_body('https://httpbin.org/delay/%s' % x) for x in args.x]
    # Yield the futures one by one
    for future in futures:
        yield future
