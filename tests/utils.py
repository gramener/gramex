# -*- coding: utf-8 -*-
'Test case utilities'

import json
import time
import random
import pandas as pd
from tornado import gen
from tornado.web import RequestHandler
from tornado.escape import recursive_unicode
from tornado.httpclient import AsyncHTTPClient
from concurrent.futures import ThreadPoolExecutor
from gramex.services import info

watch_info = []
ws_info = []


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


def attributes(self):
    assert self.name == 'func/attributes'
    assert self.conf.pattern == '/func/attributes'
    assert self.kwargs['function'] == 'utils.attributes'
    assert self.session['id']
    return 'OK'


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


def httpbin(handler, mime='json', rand=None, status=200):
    '''
    Prints all request parameters. Accepts the following arguments:

    - ?mime=[json|html]
    - ?rand=<number>
    - ?status=<code>
    '''
    mime_type = {
        'json': 'application/json',
        'html': 'text/html',
    }

    response = {
        'headers': {key: handler.request.headers.get(key) for key in handler.request.headers},
        'args': recursive_unicode(handler.request.arguments),
    }
    rand = handler.get_argument('rand', rand)
    if rand is not None:
        response['rand'] = random.randrange(int(rand))

    handler.set_status(status)
    handler.set_header('Content-Type', mime_type[mime])
    return json.dumps(response, indent=4)


def on_created(event):
    watch_info.append({'event': event, 'type': 'created'})


def on_modified(event):
    watch_info.append({'event': event, 'type': 'modified'})


def on_deleted(event):
    watch_info.append({'event': event, 'type': 'deleted'})


def slow_count(var, count=1, delay=0.01):
    for x in range(count):
        info[var] = x
        time.sleep(delay)


def session(handler):
    var = handler.get_argument('var', None)
    if var is not None:
        handler.session['var'] = var
    return json.dumps(handler.session, indent=4)


def logtest(handler):
    result = {}

    def log_method(s):
        result['log'] = s

    handler.log_request(log_method)
    return result['log']


def zero_division_error(handler):
    '''Dummy function that raises a ZeroDivisionError exception'''
    1 / 0


def handle_error(status_code, kwargs, handler):
    return json.dumps({
        'status_code': status_code,
        'kwargs': repr(kwargs),
        'handler.request.uri': handler.request.uri,
    })


def set_session(handler, **kwargs):
    for key, value in kwargs.items():
        handler.session[key] = value


def increment(handler):
    '''
    This function is used to check the cache. Suppose we fetch a page, then
    Gramex is restarted, and we fetch it again. Gramex recomputes the results,
    which don't change. So the ETag will match the browser. Then Gramex returns a
    304.

    This 304 must still be cached as a 200, with the correct result.
    '''
    info.increment = 1 + info.get('increment', 0)
    return 'Constant result'


def ws_open(handler):
    ws_info.append({'method': 'open'})


def ws_on_close(handler):
    ws_info.append({'method': 'on_close'})


def ws_on_message(handler, message):
    ws_info.append({'method': 'on_message', 'message': message})


def ws_info_dump(handler):
    result = json.dumps(ws_info, indent=4)
    del ws_info[:]
    return result
