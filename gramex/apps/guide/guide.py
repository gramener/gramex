'''
Utility functions for gramex-guide
'''

import yaml
import markdown
import gramex

md = markdown.Markdown(extensions=[
    'markdown.extensions.extra',
    'markdown.extensions.meta',
    'markdown.extensions.codehilite',
    'markdown.extensions.smarty',
    'markdown.extensions.sane_lists',
    'markdown.extensions.fenced_code',
    'markdown.extensions.toc',
], output_format='html5')


def markdown_template(content, handler):
    kwargs = {
        'classes': '',
        # GUIDE_ROOT has the absolute URL of the Gramex guide
        'GUIDE_ROOT': gramex.config.variables.GUIDE_ROOT,
        'body': md.convert(content),
    }
    for key, val in md.Meta.items():
        kwargs[key] = val[0]
    if 'xsrf' in content:
        handler.xsrf_token
    return gramex.cache.open(
        'markdown.template.html', 'template', rel=True).generate(**kwargs).decode('utf-8')


def config(handler):
    '''Dump the final resolved config'''
    return yaml.dump(gramex.conf, default_flow_style=False)
