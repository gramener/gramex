'Test case utilities'

import json
import pandas as pd
from tornado import gen
from tornado.web import RequestHandler
from tornado.httpclient import AsyncHTTPClient
from concurrent.futures import ThreadPoolExecutor

watch_info = []


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


def iterator(handler):
    for val in handler.get_arguments('x'):
        yield str(val)


def str_callback(value, callback):
    callback(str(value))


def iterator_async(handler):
    for val in handler.get_arguments('x'):
        future = gen.Task(str_callback, val)
        yield future


@gen.coroutine
def async_args(*args, **kwargs):
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


thread_pool = ThreadPoolExecutor(4)


def count_group(df, col):
    return df.groupby(col)[col].count()


@gen.coroutine
def async_calc(handler):
    rows = 1000
    cols = ['A', 'B', 'C']
    df = pd.DataFrame(
        pd.np.arange(rows * len(cols)).reshape((rows, len(cols))),
        columns=cols)
    df = df % 4
    counts = yield [thread_pool.submit(count_group, df, col) for col in cols]
    # result is [[250,250,250],[250,250,250],[250,250,250],[250,250,250]]
    raise gen.Return(pd.concat(counts, axis=1).to_json(orient='values'))


def on_created(event):
    watch_info.append({'event': event, 'type': 'created'})


def on_modified(event):
    watch_info.append({'event': event, 'type': 'modified'})


def on_deleted(event):
    watch_info.append({'event': event, 'type': 'deleted'})
