import tornado.gen
import tornado.template
from cachetools import LRUCache

# A fixed number of templates are compiled and cached
template_cache = LRUCache(maxsize=1000)


@tornado.gen.coroutine
def template(content, handler=None, **kwargs):
    if content in template_cache:
        tmpl = template_cache[content]
    else:
        tmpl = template_cache[content] = tornado.template.Template(content)
    raise tornado.gen.Return(tmpl.generate(handler=handler, **kwargs).decode('utf-8'))
