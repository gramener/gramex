import json
from tornado import gen
from tornado.web import RequestHandler
from tornado.httpclient import AsyncHTTPClient


def args_as_json(handler):
    return json.dumps({arg: handler.get_arguments(arg) for arg in handler.request.arguments},
                      sort_keys=True)


def params_as_json(*args, **kwargs):
    args = list(args)
    callback = kwargs.pop('callback', None)
    for index, arg in enumerate(args):
        if isinstance(arg, RequestHandler):
            args[index] = 'Handler'
    for key, arg in kwargs.items():
        if isinstance(arg, RequestHandler):
            kwargs[key] = 'Handler'
    result = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
    if callable(callback):
        callback(result)
    else:
        return result

@gen.coroutine
def async_task(*args, **kwargs):
    'Run params_as_json asynchronously'
    result = yield gen.Task(params_as_json, *args, **kwargs)
    raise gen.Return(result)


@gen.coroutine
def async_http(url):
    'Fetch a URL asynchronously'
    httpclient = AsyncHTTPClient()
    result = yield httpclient.fetch(url)
    raise gen.Return(result.body)


@gen.coroutine
def async_http2(url1, url2):
    'Fetch two URLs asynchronously'
    httpclient = AsyncHTTPClient()
    r1, r2 = yield [httpclient.fetch(url1), httpclient.fetch(url2)]
    raise gen.Return(r1.body + r2.body)
