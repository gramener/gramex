import tornado.gen
import tornado.template


@tornado.gen.coroutine
def template(content, **kwargs):
    tmpl = tornado.template.Template(content)
    raise tornado.gen.Return(tmpl.generate(**kwargs).decode('utf-8'))
