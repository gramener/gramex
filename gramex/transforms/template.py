import os
import tornado.gen
import tornado.template
import gramex.cache


@tornado.gen.coroutine
def template(content, handler=None, **kwargs):
    '''Renders a file as a Tornado template in FileHandler.

    This can be used as a keyword argument to FileHandler:

    ```yaml
    pattern: /file.tmpl.html
    handler: FileHandler
    kwargs:
        ...
        template: '*.tmpl.html'
    ```
    '''
    name = f'{handler.name}:template'
    loader = None
    # If a FileHandler renders templates, cache the file, and treat handler.file as filename.
    if handler is not None and getattr(handler, 'file', None):
        name = str(handler.file)
        loader = CacheLoader(os.path.dirname(str(handler.file)))
    tmpl = tornado.template.Template(content, name=name, loader=loader)

    if handler is not None:
        for key, val in handler.get_template_namespace().items():
            kwargs.setdefault(key, val)

    # handler is added to kwargs by handler.get_template_namespace()
    return tmpl.generate(**kwargs).decode('utf-8')


@tornado.gen.coroutine
def scss(content, handler):
    '''Renders a SCSS file as CSS in a FileHandler.

    This can be used as a keyword argument to FileHandler:

    ```yaml
    pattern: /file.scss
    handler: FileHandler
    kwargs:
        ...
        scss: '*.scss'
    ```
    '''
    from gramex.apps.ui import sass2

    # Ignore the content provided. sass2 needs the file actually located at handler.path.
    result = yield sass2(handler, handler.path)
    return result.decode('utf-8')


# SCSS files and SASS files are compiled exactly the same way
sass = scss


@tornado.gen.coroutine
def ts(content, handler):
    '''Render a TypeScript file as JavaScript in a FileHandler.

    This can be used as a keyword argument to FileHandler:

    ```yaml
    pattern: /file.ts
    handler: FileHandler
    kwargs:
        ...
        ts: '*.ts'
    ```
    '''
    from gramex.apps.ui import ts

    # Ignore the content provided. ts needs the file actually located at handler.path.
    result = yield ts(handler, handler.path)
    return result.decode('utf-8')


@tornado.gen.coroutine
def vue(content, handler):
    '''Renders a Vue file as JS web component via @vue/cli in a FileHandler.

    This can be used as a keyword argument to FileHandler:

    ```yaml
    pattern: /file.vue
    handler: FileHandler
    kwargs:
        ...
        template: '*.vue'
    ```
    '''
    from gramex.apps.ui import vue

    # Ignore the content provided. vue needs the file actually located at handler.path.
    result = yield vue(handler, handler.path)
    return result.decode('utf-8')


class CacheLoader(tornado.template.Loader):
    # Like tornado.template.Loader, but caching only until underlying file is changed.
    # Used internally by BaseHandler to override the Tornado default template loader.

    def load(self, name, parent_path=None):
        # Always load the file. _create_template takes care of the caching
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
