from __future__ import unicode_literals

import os
from gramex.config import variables
from tornado.escape import xhtml_escape

folder = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(folder, 'config.yaml')
ui_config_file = os.path.join(variables['GRAMEXPATH'], 'apps', 'ui', 'config.yaml')


def view_source(html):
    '''Return the HTML with an escaped view source block appended to it'''
    s = html.decode('utf-8')
    return ('<div class="viewsource-wrapper">' + s +
            '<pre class="viewsource"><code class="language-html">' + xhtml_escape(s.strip()) +
            '</code></pre></div>')


def only_source(html):
    '''Return only the escaped view source block'''
    s = html.decode('utf-8')
    return ('<pre class="viewsource"><code class="language-html">' + xhtml_escape(s.strip()) +
            '</code></pre>')
