import json
import tornado.web
import tornado.gen
from types import GeneratorType
from gramex.transforms import build_transform
from gramex.config import app_log, CustomJSONEncoder
from .basehandler import BaseHandler


class FunctionHandler(BaseHandler):
    '''Renders the output of a function when the URL is called via GET or POST.

    - `function`: A Python expression that can use `handler` as a variable.
    - `headers`: HTTP headers to set on the response.
    - `redirect`: URL to redirect to when done, e.g. for calculations without output.

    The function result is converted to a string and rendered.
    You can also yield one or more results. These are written immediately, in order.
    '''

    @classmethod
    def setup(cls, headers={}, **kwargs):
        super(FunctionHandler, cls).setup(**kwargs)
        # Don't use cls.info.function = build_transform(...) -- Python treats it as a method
        cls.info = {}
        cls.info['function'] = build_transform(
            kwargs, vars={'handler': None}, filename=f'url:{cls.name}'
        )
        cls.headers = headers
        cls.post = cls.put = cls.delete = cls.patch = cls.get
        if not kwargs.get('cors'):
            cls.options = cls.get

    @tornado.gen.coroutine
    def get(self, *path_args):
        if self.redirects:
            self.save_redirect_page()

        if 'function' not in self.info:
            raise ValueError(f'Invalid function definition in url:{self.name}')
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
            # To check if item is a numpy object, avoid isinstance(numpy.int8), etc.
            # Importing numpy is slow. Instead, check the class name.
            # Strip trailing numbers (e.g. int8, int16, int32)
            # Strip trailing underscore (e.g. str_, bytes_)
            # Strip leading 'u' (e.g. uint, ulong)
            cls = type(item).__name__.rstrip('0123456789_').lstrip('u')
            if isinstance(item, (bytes, str)):
                self.write(item)
                if multipart:
                    self.flush()
            # Ignore None as a return type
            elif item is None:
                pass
            # Allow ANY type that can be converted by CustomJSONEncoder.
            # This includes JSON types, detected by isinstance(item, ...))
            # and numpy types, detected by cls in (...)
            # and anything with a to_dict, e.g. DataFrames
            elif (
                isinstance(item, (int, float, bool, list, tuple, dict))
                or cls in ('datetime', 'int', 'intc', 'float', 'bool', 'ndarray', 'bytes', 'str')
                or hasattr(item, 'to_dict')
            ):
                self.write(
                    json.dumps(
                        item, separators=(',', ':'), ensure_ascii=True, cls=CustomJSONEncoder
                    )
                )
                if multipart:
                    self.flush()
            else:
                app_log.warning(
                    f'url:{self.name}: FunctionHandler can write scalars/list/dict, '
                    f'not {type(item)}: {item!r}'
                )

        if self.redirects:
            self.redirect_next()
