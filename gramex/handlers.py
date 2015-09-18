import os
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
