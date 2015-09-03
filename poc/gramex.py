import config
import logging
import tornado.web

# The global conf holds the current configuration
conf = config.load()


class TemplateHandler(tornado.web.RequestHandler):
    def initialize(self, **kwargs):
        self.kwargs = kwargs

    def get(self):
        self.write('TemplateHandler:<p>{:s}</p>'.format(
            str(self.kwargs)))

if __name__ == '__main__':
    # Configure logging
    logging.config.dictConfig(conf.log)

    # Configure URL handlers
    handlers = []
    for name, spec in conf.url.items():
        if not isinstance(spec.handler, tornado.web.RequestHandler):
            # TODO: evaluate only in the context of handlers
            spec.handler = eval(spec.handler)
        handlers.append(tornado.web.URLSpec(name=name, **spec))

    # Configure application
    application = tornado.web.Application(**conf.app.settings)
    application.add_handlers(".*$", handlers)
    application.listen(**conf.app.listen)

    # Start application
    logging.warn('Starting Gramex on %s', conf.app.listen.port)
    tornado.ioloop.IOLoop.current().start()
