'''
Utility functions for gramex-guide
'''

import os
import yaml
import string
import markdown
from orderedattrdict import DefaultAttrDict
import gramex


folder = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(folder, 'markdown.template')
md = markdown.Markdown(extensions=[
    'markdown.extensions.extra',
    'markdown.extensions.meta',
    'markdown.extensions.codehilite',
    'markdown.extensions.smarty',
    'markdown.extensions.sane_lists',
    'markdown.extensions.fenced_code',
    'markdown.extensions.toc',
], output_format='html5')
stringtemplate = gramex.cache.opener(string.Template, read=True)


def markdown_template(content, handler):
    # Template has optional parameters like $title. DefaultAttrDict prevents errors.
    kwargs = DefaultAttrDict(str)
    # GUIDE_ROOT has the absolute URL of the Gramex guide
    kwargs.GUIDE_ROOT = gramex.config.variables.GUIDE_ROOT
    kwargs.body = md.convert(content)
    for key, val in md.Meta.items():
        kwargs[key] = val[0]
    if 'xsrf' in content:
        handler.xsrf_token
    return gramex.cache.open(template_path, stringtemplate).substitute(kwargs)


def config(handler):
    '''Dump the final resolved config'''
    return yaml.dump(gramex.conf, default_flow_style=False)
