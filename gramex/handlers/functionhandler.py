import json
from functools import wraps
from inspect import signature
import tornado.web
import tornado.gen
from types import GeneratorType
from typing import get_type_hints
from gramex.transforms import build_transform
from gramex.config import app_log, CustomJSONEncoder
from .basehandler import BaseHandler
from tornado.util import unicode_type


def _parse_handler(handler, sig):
    if handler.request.method in ('GET', 'DELETE'):
        if handler.path_args:
            args, kwargs = handler.path_args, {}
        else:
            arguments = {k: v[0] if len(v) == 1 else v for k, v in handler.args.items()}
            arguments = {k: v for k, v in arguments.items() if k in sig.parameters}
            args, kwargs = [], {}
            for arg, val in arguments.items():
                param = sig.parameters[arg]
                if param.kind == param.VAR_POSITIONAL:
                    args.extend(val)
                elif param.kind == param.POSITIONAL_ONLY:
                    args.append(val)
                elif param.kind in (param.KEYWORD_ONLY, param.POSITIONAL_OR_KEYWORD):
                    kwargs[arg] = val
    elif handler.request.method in ('POST', 'PUT'):
        args = []
        try:
            kwargs = json.loads(handler.request.body)
        except (TypeError, json.JSONDecodeError):
            kwargs = {k: v[0] if len(v) == 1 else v for k, v in handler.args.items()}
        kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
    return args, kwargs


def add_handler(func):
    """Wrap a function to make it compatible with a tornado.web.RequestHandler

    Use this decorator if you'd rather not write a FunctionHandler function from scratch,
    but reuse an existing one.

    Parameters
    ----------
    func : callable
        function to be wrapped.

    Usage
    -----
    Suppose you have the following function in `greet.,py`:

    def birthday(name, age):
        return f'{name} turns {age} today! Happy Birthday!'

    Then, in `gramex.yaml`, you can use it as a FunctionHandler as follows:
    url:
        pattern: /$YAMLURL/greet
        handler: FunctionHandler
        kwargs:
            funtion: gramex.handlers.functionhandler.add_handler(greet.birthday)(handler)

    Now, `/greet?name=Gramex&age=10` returns "Gramex turns 10 today! Happy Birthday!".
    An alternate way of configuring this is as follows:

    url:
        pattern: /$YAMLURL/greet/name/(.*)/age/(.*)
        handler: FunctionHandler
        kwargs:
            funtion: gramex.handlers.functionhandler.add_handler(greet.birthday)(handler)

    Here, `/greet/name/Gramex/age/10` returns "Gramex turns 10 today! Happy Birthday!".
    `add_handler` can also be used as a decorator,

    @add_handler
    def birthday(name, age):
        return f'{name} turns {age} today! Happy Birthday!'

    which simplifies the FunctionHandler configuration in `gramex.yaml` as follows:
    url:
        pattern: /$YAMLURL/greet
        handler: FunctionHandler
        kwargs:
            funtion: greet.birthday  # notice that calling the wrapper is not required here

    Arbitrary functions can be wrapped with `add_handler`. However, it does make some assumptions:

    1. In a GET and DELETE requests, `handler.path_args` are converted to positional arguments,
    and URL parameters are converted to keyword arguments.
    2. In POST andd PUT requests, `handler.request.body` is deserialized and passed directly to
    the wrapped function as a dict of keyword arguments. URL parameters and path arguments
    are _ignored_.

    The wrapper also naively tries to enforce types based on any type annotations that are found
    in the wrapped function.

    Note that this alone does not guarantee RESTfulness. This function simply translates
    handler data and attempts to typecast inputs to the required format.
    """
    sig = signature(func)

    @wraps(func)
    def wrapper(handler):
        args, kwargs = _parse_handler(handler, sig)
        hints = get_type_hints(func)
        for arg, argtype in hints.items():
            if argtype is not type(None):  # NOQA: E721
                if argtype is bool:
                    args = [json.loads(k) for k in args]
                    named_arg = kwargs.get(arg)
                    if named_arg:
                        try:
                            named_arg = json.loads(named_arg)
                        except json.JSONDecodeError:
                            pass
                        kwargs[arg] = named_arg
                param = sig.parameters.get(arg, False)
                if param:
                    if param.kind == param.VAR_POSITIONAL:
                        args = [argtype(k) for k in args]
                    else:
                        kwargs[arg] = argtype(kwargs[arg])
        return json.dumps(func(*args, **kwargs))

    return wrapper


class FunctionHandler(BaseHandler):
    '''
    Renders the output of a function when the URL is called via GET or POST. It
    accepts these parameters when initialized:

    :arg string function: a string that resolves into any Python function or
        method (e.g. ``str.lower``). By default, it is called as
        ``function(handler)`` where handler is this RequestHandler, but you can
        override ``args`` and ``kwargs`` below to replace it with other
        parameters. The result is rendered as-is (and hence must be a string, or
        a Future that resolves to a string.) You can also yield one or more
        results. These are written immediately, in order.
    :arg list args: positional arguments to be passed to the function.
    :arg dict kwargs: keyword arguments to be passed to the function.
    :arg dict headers: HTTP headers to set on the response.
    :arg list methods: List of HTTP methods to allow. Defaults to
        `['GET', 'POST']`.
    :arg string redirect: URL to redirect to when the result is done. Used to
        trigger calculations without displaying any output.
    '''
    @classmethod
    def setup(cls, headers={}, methods=['GET', 'POST'], **kwargs):
        super(FunctionHandler, cls).setup(**kwargs)
        # Don't use cls.info.function = build_transform(...) -- Python treats it as a method
        cls.info = {}
        cls.info['function'] = build_transform(kwargs, vars={'handler': None},
                                               filename='url: %s' % cls.name)
        cls.headers = headers
        for method in (methods if isinstance(methods, (tuple, list)) else [methods]):
            setattr(cls, method.lower(), cls._get)

    @tornado.gen.coroutine
    def _get(self, *path_args):
        if self.redirects:
            self.save_redirect_page()

        if 'function' not in self.info:
            raise ValueError('Invalid function definition in url:%s' % self.name)
        result = self.info['function'](handler=self)
        for header_name, header_value in self.headers.items():
            self.set_header(header_name, header_value)

        # Use multipart to check if the respose has multiple parts. Don't
        # flush unless it's multipart. Flushing disables Etag
        multipart = isinstance(result, GeneratorType) or len(result) > 1

        # build_transform results are iterable. Loop through each item
        for item in result:
            # Resolve futures and write the result immediately
            if tornado.concurrent.is_future(item):
                item = yield item
            if isinstance(item, (bytes, unicode_type, dict)):
                self.write(json.dumps(item, separators=(',', ':'), ensure_ascii=True,
                                      cls=CustomJSONEncoder) if isinstance(item, dict) else item)
                if multipart:
                    self.flush()
            else:
                app_log.warning('url:%s: FunctionHandler can write strings/dict, not %s',
                                self.name, repr(item))

        if self.redirects:
            self.redirect_next()
