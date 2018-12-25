import os
import tornado.gen
import tornado.template
from cachetools import LRUCache

# A fixed number of templates are compiled and cached
template_cache = LRUCache(maxsize=1000)


def template_sync(content, handler=None, **kwargs):
    '''
    Renders template from content.

    If the handler has a ``.path`` attribute, or ``path=`` is passed, makes a
    ``T()`` function available to templates that can render sub-templates.

    ``T(tmpl_path, x=1)`` renders the template from ``tmpl_path`` relative to
    the calling path, passing:

    - ``handler`` -- passed directly from the parent template
    - ``path`` -- absolute path of ``tmpl_path`` relative to parent template's
      ``path``
    - ``**kwargs`` -- from the parent template
    - ``x=1`` -- any other parameters added when invoking ``T()``

    ``T()`` can only be used to render UTF-8 encoded text, not binary files.
    '''
    if content in template_cache:
        tmpl = template_cache[content]
    else:
        tmpl = template_cache[content] = tornado.template.Template(content)

    # If the handler has a .path attribute, or kwargs has a path,
    # templates can use a T() function that renders templates relative to path.
    path = str(
        kwargs['path'] if 'path' in kwargs else
        getattr(handler, 'path', '') if handler is not None else
        ''
    )
    if path:
        import gramex.cache
        from gramex.config import merge
        root = os.path.dirname(path)

        def T(tmpl_path, **tmpl_kwargs):
            path = os.path.abspath(os.path.join(root, tmpl_path))
            content = gramex.cache.open(path, 'txt')
            merge(tmpl_kwargs, kwargs, mode='setdefault')
            tmpl_kwargs['path'] = path
            return template_sync(content, handler=handler, **tmpl_kwargs)

        kwargs['T'] = T
        kwargs['path'] = path

    return tmpl.generate(handler=handler, **kwargs).decode('utf-8')


@tornado.gen.coroutine
def template(content, handler=None, **kwargs):
    '''
    Renders template from content. Used as a transform in any handler, mainly
    FileHandler.
    '''
    result = template_sync(content, handler, **kwargs)
    raise tornado.gen.Return(result)
