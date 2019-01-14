import os
import tornado.gen
import tornado.template
from cachetools import LRUCache

# A fixed number of templates are compiled and cached
template_cache = LRUCache(maxsize=1000)


@tornado.gen.coroutine
def template(content, handler=None, **kwargs):
    '''
    Renders template from content. Used as a transform in any handler, mainly
    FileHandler.
    '''
    if content in template_cache:
        tmpl = template_cache[content]
    else:
        loader = None
        if handler is not None and getattr(handler, 'path', None):
            loader = tornado.template.Loader(os.path.dirname(str(handler.path)))
        tmpl = template_cache[content] = tornado.template.Template(content, loader=loader)

    if handler is not None:
        for key, val in handler.get_template_namespace().items():
            kwargs.setdefault(key, val)

    # handler is added to kwargs by handler.get_template_namespace()
    raise tornado.gen.Return(tmpl.generate(**kwargs).decode('utf-8'))
