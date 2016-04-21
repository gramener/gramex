'''
Utility functions for gramex-guide
'''

import io
import os
import yaml
import string
import markdown
from orderedattrdict import AttrDict, DefaultAttrDict
import gramex


_template = AttrDict(
    root=os.path.dirname(os.path.abspath(__file__)),
    markdown=markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.meta',
        'markdown.extensions.codehilite',
        'markdown.extensions.smarty',
        'markdown.extensions.headerid',
    ], output_format='html5'),
)


def load_markdown_template(event=None):
    with io.open(os.path.join(_template.root, 'markdown.template'), encoding='utf-8') as handle:
        _template.template = string.Template(handle.read())


def markdown_template(content, handler):
    kwargs = DefaultAttrDict(str)
    kwargs.body = _template.markdown.convert(content)
    for key, val in _template.markdown.Meta.items():
        kwargs[key] = val[0]
    # guide_root has the relative URL from the displayed file to gramex-guide root
    folder = str(handler.file / '..')
    kwargs.guide_root = os.path.relpath(_template.root, folder).replace(os.path.sep, '/')
    return _template.template.substitute(kwargs)


def config(handler):
    'Dump the final resolved config'
    return yaml.dump(gramex.conf, default_flow_style=False)


# On startup, load the markdown template once
load_markdown_template()
