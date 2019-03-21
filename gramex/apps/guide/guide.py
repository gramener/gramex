'''
Utility functions for gramex-guide
'''

import cachetools
import gramex
import markdown
import yaml

md = markdown.Markdown(extensions=[
    'markdown.extensions.extra',
    'markdown.extensions.meta',
    'markdown.extensions.codehilite',
    'markdown.extensions.smarty',
    'markdown.extensions.sane_lists',
    'markdown.extensions.fenced_code',
    'markdown.extensions.toc',
], output_format='html5')
# Create a cache for guide markdown content
md_cache = cachetools.LRUCache(maxsize=5000000, getsizeof=len)


def markdown_template(content, handler):
    if content not in md_cache:
        md_cache[content] = {
            'content': md.convert(content),
            'meta': md.Meta
        }
    content = md_cache[content]
    kwargs = {
        'classes': '',
        # GUIDE_ROOT has the absolute URL of the Gramex guide
        'GUIDE_ROOT': gramex.config.variables.GUIDE_ROOT,
        'body': content['content'],
        'title': ''
    }
    for key, val in content['meta'].items():
        kwargs[key] = val[0]
    if 'xsrf' in content:
        handler.xsrf_token
    return gramex.cache.open(
        'markdown.template.html', 'template', rel=True).generate(**kwargs).decode('utf-8')


def config(handler):
    '''Dump the final resolved config'''
    return yaml.dump(gramex.conf, default_flow_style=False)
