import tornado.web


class TemplateHandler(tornado.web.RequestHandler):
    def initialize(self, **kwargs):
        self.kwargs = kwargs

    def get(self):
        self.write('TemplateHandler:<p>{:s}</p>'.format(
            str(self.kwargs)))
