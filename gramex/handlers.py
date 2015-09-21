import os
import yaml
import xmljson
import lxml.html
from pathlib import Path
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from tornado.web import HTTPError, RequestHandler, StaticFileHandler
from zope.dottedname.resolve import resolve


class Function(RequestHandler):
    def initialize(self, function, kwargs={}, redirect=None):
        self.function = resolve(function)
        self.kwargs = kwargs
        self.redirect_url = redirect

    def get(self):
        self.function(**self.kwargs)
        self.redirect(self.redirect_url or self.request.headers.get('Referer', '/'))


class DirectoryHandler(StaticFileHandler):
    def validate_absolute_path(self, root, absolute_path):
        '''
        Return directory itself for directory
        '''
        root = os.path.abspath(root) + os.path.sep
        # The trailing slash also needs to be temporarily added back
        # the requested path so a request to root/ will match.
        if not (absolute_path + os.path.sep).startswith(root):
            raise HTTPError(403, "%s is not in root static directory",
                            self.path)
        if os.path.isdir(absolute_path):
            if not self.request.path.endswith("/"):
                self.redirect(self.request.path + "/", permanent=True)
                return
            if self.default_filename is not None:
                default_file = os.path.join(absolute_path, self.default_filename)
                if os.path.isfile(default_file):
                    return default_file
            # Now, we have a directory ending with "/" without a
            # default_filename, so just allow it.
            return absolute_path
        if not os.path.exists(absolute_path):
            raise HTTPError(404)
        if not os.path.isfile(absolute_path):
            raise HTTPError(403, "%s is not a file", self.path)
        return absolute_path

    @classmethod
    def get_content(cls, abspath, start=None, end=None):
        if os.path.isdir(abspath):
            content = ['<h1>Index of %s </h1><ul>' % abspath]
            for name in os.listdir(abspath):
                content.append('<li><a href="%s">%s</a></li>' % (name, name))
            content.append('</ul>')
        else:
            content = super(DirectoryHandler, cls).get_content(abspath, start, end)
        if not isinstance(content, bytes):
            content = ''.join(content)
        return content

    def get_content_size(self):
        if os.path.isdir(self.absolute_path):
            return len(self.get_content(self.absolute_path))
        return super(DirectoryHandler, self).get_content_size()

    def get_content_type(self):
        if os.path.isdir(self.absolute_path):
            return 'text/html'
        return super(DirectoryHandler, self).get_content_type()


class TransformHandler(RequestHandler):
    '''
    Renders files in a path after transforming them. This is useful for a static
    file handler that pre-processes responses. Here are some examples::

        pattern: /help/(.*)
        handler: gramex.handlers.TransformHandler   # This handler
        kwargs:
          path: help/                               # Serve files from help/
          default_filename: index.yaml              # Directory index file
          transform:
            "*.md":                                 # Any file matching .md
              transform: markdown.markdown          #   Convert .md to html
              headers:
                Content-Type: text/html             #   MIME type: text/html
            "*.yaml":                               # YAML files use BadgerFish
              transform: gramex.handlers.TransformHandler.badgerfish
              headers:
                Content-Type: text/html             #   MIME type: text/html
            "*.lower":                              # Any .lower file
              transform: string.lower               #   Convert to lowercase
              headers:
                Content-Type: text/plain            #   Serve as plain text

    TODO:

    - Write test cases
    - Make this async
    - Cache it
    '''
    @staticmethod
    def badgerfish(content):
        data = yaml.load(content, Loader=AttrDictYAMLLoader)
        return lxml.html.tostring(xmljson.badgerfish.etree(data)[0],
                                  doctype='<!DOCTYPE html>')

    def initialize(self, path, default_filename=None, transform={}):
        self.root = path
        self.default_filename = default_filename
        self.transform = {}
        for pattern, trans in transform.items():
            trans = dict(trans)
            if 'transform' in trans:
                trans['transform'] = resolve(trans['transform'])
            self.transform[pattern] = trans

    def get(self, path):
        self.path = path
        if os.path.sep != '/':
            self.path = self.path.replace('/', os.path.sep)
        absolute_path = os.path.abspath(os.path.join(self.root, self.path))

        if (os.path.isdir(absolute_path) and
                self.default_filename is not None):
            if not self.request.path.endswith("/"):
                self.redirect(self.request.path + "/", permanent=True)
                return
            absolute_path = os.path.join(absolute_path, self.default_filename)
        if not os.path.exists(absolute_path):
            raise HTTPError(404)
        if not os.path.isfile(absolute_path):
            raise HTTPError(403, "%s is not a file", self.path)

        # Python 2.7 pathlib only accepts str, not unicode
        path = Path(str(absolute_path))
        with path.open('r+b') as handle:
            content = handle.read()

        # Apply first matching transforms
        for pattern, trans in self.transform.items():
            if path.match(pattern):
                if 'transform' in trans:
                    content = trans['transform'](content)
                if 'header' in trans:
                    for header_name, header_value in trans['header'].items():
                        self.set_header(header_name, header_value)
                break

        self.write(content)
        self.flush()
