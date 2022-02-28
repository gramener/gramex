'''Test case utilities'''
import os
import csv
import sys
import json
import time
import random
import pandas as pd
import numpy as np
from io import StringIO
from collections import Counter
from orderedattrdict import AttrDict
from typing import List
from typing_extensions import Annotated
from sklearn.datasets import make_circles as sk_make_circles
from tornado import gen
from tornado.web import RequestHandler, MissingArgumentError, HTTPError
from tornado.gen import coroutine
from tornado.concurrent import Future
from tornado.httpclient import AsyncHTTPClient
from concurrent.futures import ThreadPoolExecutor
from gramex.cache import Subprocess, CustomJSONEncoder
from gramex.services import info
from gramex.services.emailer import SMTPStub
from gramex.handlers import BaseHandler
from gramex.http import OK
from gramex.transforms import handler, Header

watch_info = []
ws_info = []
state_info = []
counters = Counter()
slow = {'value': 0, 'max': 20}


def args_as_json(handler):
    return json.dumps(handler.args, sort_keys=True)


def params_as_json(*args, **kwargs):
    '''Return argument query parameters as a JSON object'''
    args = list(args)
    callback = kwargs.pop('callback', None)
    # If a passed parameters is a request handler, replace with 'Handler'
    for index, arg in enumerate(args):
        if isinstance(arg, RequestHandler):
            args[index] = 'Handler'
    for key, arg in kwargs.items():
        if isinstance(arg, RequestHandler):
            kwargs[key] = 'Handler'
    # Just dump the args as JSON
    result = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
    # If a callback was provided, pass through the callback. (Used by async_args)
    if callable(callback):
        callback(result)
    else:
        return result


def attributes(self):
    assert self.name == 'func/attributes'
    assert self.conf.pattern == '/func/attributes'
    assert self.kwargs.function == 'utils.attributes'
    assert self.conf.kwargs.function == 'utils.attributes'
    assert self.session['id']
    return 'OK'


def iterator(handler):
    for val in handler.get_arguments('x'):
        yield str(val)


def str_callback(value, callback):
    callback(str(value))


def iterator_async(handler):
    for val in handler.get_arguments('x'):
        future = Future()
        str_callback(val, callback=future.set_result)
        yield future


@gen.coroutine
def async_args(*args, **kwargs):
    '''Run params_as_json asynchronously'''
    future = Future()
    kwargs['callback'] = future.set_result
    params_as_json(*args, **kwargs)
    result = yield future
    raise gen.Return(result)


@gen.coroutine
def async_http(url):
    '''Fetch a URL asynchronously'''
    httpclient = AsyncHTTPClient()
    result = yield httpclient.fetch(url)
    raise gen.Return(result.body)


@gen.coroutine
def async_http2(url1, url2):
    '''Fetch two URLs asynchronously'''
    httpclient = AsyncHTTPClient()
    r1, r2 = yield [httpclient.fetch(url1), httpclient.fetch(url2)]
    raise gen.Return(r1.body + r2.body)


thread_pool = ThreadPoolExecutor(4)


def count_group(df, col):
    return df.groupby(col)[col].count()


@gen.coroutine
def async_calc(handler):
    '''Perform a slow calculation asynchronously'''
    rows = 1000
    cols = ['A', 'B', 'C']
    df = pd.DataFrame(
        np.arange(rows * len(cols)).reshape((rows, len(cols))),
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
        'args': handler.args,
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


def schedule_start():
    counters['schedule-key'] += 1


def schedule_key():
    return '%d' % counters['schedule-key']


def slow_count_start():
    info.schedule['schedule-slow-count'].run()
    slow['initial'] = slow['value']
    slow['running'] = True


def slow_count_check(delay=0.01):
    time.sleep(delay * 2)
    assert slow['initial'] < slow['value'], 'Schedule has not yet started'
    assert slow['value'] < slow['max'] - 1, 'Schedule is not running in parallel'
    slow['running'] = False


def slow_count(delay=0.01):
    # This runs in a thread and increments slow['value'] every 10ms
    for x in range(slow['max']):
        slow['value'] = x
        time.sleep(delay)
        # Stop the thread once test case is verified
        if not slow['running']:
            break


def session(handler):
    var = handler.get_argument('var', None)
    if var is not None:
        handler.session['var'] = var
    return json.dumps(handler.session, indent=4, cls=CustomJSONEncoder)


def encrypt(handler, content):
    return content + handler.request.headers.get('salt', '123')


def log_format(handler):
    result = {}

    def log(s):
        result['log'] = s

    try:
        1 / 0
    except ZeroDivisionError:
        handler.log_exception(*sys.exc_info())
    handler.log_request(logger=AttrDict(info=log, warn=log, error=log))
    return result['log']


def log_csv(handler):
    result = StringIO()
    writer = csv.writer(result)
    try:
        1 / 0
    except ZeroDivisionError:
        handler.log_exception(*sys.exc_info())
    handler.log_request(writer=writer, handle=AttrDict(flush=lambda: 0))
    return result.getvalue()


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


def otp(handler):
    expire = int(handler.get_argument('expire', '0'))
    return json.dumps(handler.otp(expire=expire))


def apikey(handler):
    user = {key: val[-1] for key, val in handler.args.items()}
    return json.dumps(handler.apikey(user=user or None))


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


def increment_header(handler):
    '''
    Returns a constantly incremented number in Increment: HTTP header each time.
    Does not return any output. Used as a FunctionHandler in func/redirect
    '''
    counters['header'] += 1
    handler.set_header('Increment', str(counters['header']))
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


@gen.coroutine
def subprocess(handler):
    '''Used by test_cache.TestSubprocess to check if gramex.cache.Subprocess works'''
    kwargs = {}
    if handler.args.get('out'):
        kwargs['stream_stdout'] = [handler.write] * len(handler.args['out'])
    if handler.args.get('err'):
        kwargs['stream_stderr'] = [handler.write] * len(handler.args['err'])
    if handler.args.get('buf'):
        buf = handler.args['buf'][0]
        kwargs['buffer_size'] = int(buf) if buf.isdigit() else buf
    if handler.args.get('env'):
        kwargs['env'] = dict(os.environ)
        kwargs['env'][str('GRAMEXTESTENV')] = str('test')   # env keys & values can only by str()
    handler.write('stream: ')
    proc = Subprocess(handler.args['args'], universal_newlines=True, **kwargs)
    stdout, stderr = yield proc.wait_for_exit()
    raise gen.Return(b'return: ' + stdout + stderr)


def argparse(handler):
    params = json.loads(handler.get_argument('_q'))
    args = params.get('args', [])
    typemap = {'list': list, 'str': str, 'None': None, 'int': int, 'bool': bool}
    # Convert first parameter to relevant type, if required
    if len(args) > 0:
        if args[0] in typemap:
            args[0] = typemap[args[0]]
    # Convert type: to a Python class
    kwargs = params.get('kwargs', {})
    for val in kwargs.values():
        if 'type' in val:
            val['type'] = typemap[val['type']]
    return json.dumps(handler.argparse(*args, **kwargs))


def get_arg(handler):
    result = {}
    # ?val=x&x=a&x=b returns {val: b}
    val = handler.get_arg('val', None)
    if val is not None:
        result['val'] = handler.get_arg(val)
    # ?first=x&x=a&x=b returns {val: a}
    first = handler.get_arg('first', None)
    if first is not None:
        result['first'] = handler.get_arg(first, first=True)
    # ?default=x&x=a&x=b returns {default: b}
    # ?default=na returns {default: ok}
    default = handler.get_argument('default', None)
    if default is not None:
        result['default'] = handler.get_arg(default, 'ok')
    # ?missing=na returns {missing: ok}
    missing = handler.get_argument('missing', None)
    if missing is not None:
        try:
            handler.get_arg(missing)
        except MissingArgumentError:
            result['missing'] = 'ok'
    return json.dumps(result)


def upload_transform(content):
    return dict(alpha=1, beta=1, **content)


def write_stream():
    '''
    Interleaves stdout, stderr messages: O0 E0 O1 E1 O2 E2.
    Finally prints the GRAMEX environment variable.
    Used by test_cache.TestSubprocess
    '''
    delay = 0.02
    for n in range(0, 3):
        sys.stdout.write('o%d\n' % n)
        sys.stdout.flush()
        time.sleep(delay)
        sys.stderr.write('e%d\n' % n)
        sys.stderr.flush()
        time.sleep(delay)
    if 'GRAMEXTESTENV' in os.environ:
        sys.stdout.write('GRAMEXTESTENV: ' + os.environ['GRAMEXTESTENV'])


def sales_query(args, handler):
    '''Used by formhandler/sqlite-queryfilter and testlib.test_data.py'''
    handler.request.headers             # Check that we can access headers
    cities = args.get('ct', [])
    if len(cities) > 0:
        vals = ', '.join("'%s'" % v for v in cities)
        return 'SELECT * FROM sales WHERE city IN (%s)' % vals
    else:
        return 'SELECT * FROM sales'


def auth_prepare(args, handler):
    if 'password' in args:
        args['password'][0] += '1'


def email_stubs(handler):
    return json.dumps(SMTPStub.stubs)


def numpytypes(handler):
    supported_types = {
        'int8', 'int16', 'int32', 'int64',
        'uint8', 'uint16', 'uint32', 'uint64',
        'float16', 'float32', 'float64',
        'bool_', 'object_', 'string_', 'unicode_'}
    result = {t: getattr(np, t)(1) for t in supported_types}
    return result


def proxy_prepare(request, handler):
    request.headers['X-Prepare'] = handler.request.method
    # Add a ?b=1 if other arguments already exist
    if '?' in request.url:
        request.url = request.url + '&b=1'


def proxy_modify(request, response, handler):
    response.headers['X-Modify'] = handler.request.method


def sms_info(handler):
    result = {}
    for key, obj in info.get('sms', {}).items():
        result[key] = {'cls': type(obj).__name__}
        result[key].update({k: str(v) for k, v in vars(obj).items()})
    return result


class CounterHandler(BaseHandler):
    @classmethod
    def setup(cls, **kwargs):
        super(CounterHandler, cls).setup(**kwargs)
        counters['counterhandler'] += 1

    def get(self):
        self.write('%d' % counters['counterhandler'])


def drivehandler_modify(data, key, handler):
    if handler.request.method == 'GET':
        data['m'] = 'OK'
    return data


def gramexlog_delete(handler):
    # Delete all indices and clear all queues
    for app, app_config in info.gramexlog.apps.items():
        app_config.queue.clear()
        if app != 'nonexistent':
            app_config.conn.indices.delete(index=app, ignore=[404])


def gramexlog_search(handler, interval=0.2):
    info.gramexlog.push()
    # ElasticSearch may need some time to re-index. This can vary across systems
    time.sleep(interval)
    app = handler.get_arg('index')
    app_config = info.gramexlog.apps[app]
    results = app_config.conn.search(index=app_config.get('index', app), ignore=[404])
    results = results.get('hits', {}).get('hits', [])
    return {'hits': [result['_source'] for result in results]}


def state(*args):
    state_info.extend(args)


def get_state_info():
    return state_info


def make_circles():
    X, y = sk_make_circles(noise=0.05, factor=0.4)  # NOQA: N806
    out = os.path.join(os.path.dirname(__file__), 'circles.csv')
    pd.DataFrame(np.c_[X, y], columns=['X1', 'X2', 'y']).to_csv(
        out, encoding='utf-8', index=False)


def transform_circles(df, *argss, **kwargs):
    df[['X1', 'X2']] = np.exp(-df[['X1', 'X2']].values ** 2)
    return df


@coroutine
def pynode_run(handler):
    from gramex.pynode import node
    kwargs = {}
    for key, vals in handler.args.items():
        try:
            kwargs[key] = float(vals[-1])
        except ValueError:
            kwargs[key] = vals[-1]
    result = yield node.js(**kwargs)
    return result


@handler
def test_function(
        li1: List[int],
        lf1: List[float],
        li2: Annotated[List[int], 'List of ints'],  # noqa
        lf2: Annotated[List[float], 'List of floats'],  # noqa
        li3: List[int] = [0],
        lf3: List[float] = [0.0],
        l1=[],
        i1: Annotated[int, 'First value'] = 0,  # noqa
        i2: Annotated[int, 'Second value'] = 0,  # noqa
        s1: str = 'Total',
        n1: int = 0,
        n2: np.int64 = 0,
        h: Header = '',
        code: int = OK):
    '''
    This is a **Markdown** docstring.
    '''
    if code == OK:
        return json.dumps([li1, li2, li3, lf1, lf2, lf3, l1, i1, i2, s1, h])
    else:
        raise HTTPError(code)


if __name__ == '__main__':
    # Call the method mentioned in the command line
    method_name = sys.argv[1]
    method = globals().get(method_name)
    method()
