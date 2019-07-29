import os.path as op
from tornado.template import Template


def get_tutorial_output_html(handler):
    from ipdb import set_trace; set_trace()  # NOQA
    fpath = op.join(op.dirname(__file__),
                    handler.path_args[0], 'output', 'index.html')
    try:
        with open(fpath, 'r') as fin:
            tmpl = Template(fin.read())
    except FileNotFoundError:
        return "NOT FOUND!!!!!, {}".format(handler.name)
    return tmpl.generate(handler=handler)
