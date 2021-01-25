import os
import tornado.gen
import tornado.template
import gramex.cache


class CacheLoader(tornado.template.Loader):
    def load(self, name, parent_path=None):
        # Identical to tornado.template.Loader.load, but ALWAYS creates
        # template, even if it's cached -- because _create_template caches it
        name = self.resolve_path(name, parent_path=parent_path)
        with self.lock:
            self.templates[name] = self._create_template(name)
            return self.templates[name]

    def _template_opener(self, path):
        with open(path, 'rb') as f:
            return tornado.template.Template(f.read(), name=self._name, loader=self)

    def _create_template(self, name):
        # Use gramex.cache.open to ensure that the file is cached
        self._name = name
        return gramex.cache.open(os.path.join(self.root, name), self._template_opener)


@tornado.gen.coroutine
def template(content, handler=None, **kwargs):
    '''
    Renders template from content. Used as a transform in any handler, mainly
    FileHandler.
    '''
    loader = None
    if handler is not None and getattr(handler, 'path', None):
        loader = CacheLoader(os.path.dirname(str(handler.file)))
    tmpl = tornado.template.Template(content, loader=loader)

    if handler is not None:
        for key, val in handler.get_template_namespace().items():
            kwargs.setdefault(key, val)

    # handler is added to kwargs by handler.get_template_namespace()
    return tmpl.generate(**kwargs).decode('utf-8')


@tornado.gen.coroutine
def scss(content, handler):
    '''
    Renders a SCSS file as CSS via node-sass.
    Ignore the content provided. node-sass needs the file actually located at handler.path.
    '''
    from gramex.apps.ui import sass2
    result = yield sass2(handler, handler.path)
    return result.decode('utf-8')


# SCSS files and SASS files are compiled exactly the same way
sass = scss
