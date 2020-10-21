import json
import tornado.web
import tornado.gen
from types import GeneratorType
from gramex.transforms import build_transform
from gramex.config import app_log, CustomJSONEncoder
from .basehandler import BaseHandler
from tornado.util import unicode_type


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
