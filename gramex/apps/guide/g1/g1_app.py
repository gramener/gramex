"""Data processing functionalities."""
from __future__ import unicode_literals

import gramex.cache
from tornado.escape import xhtml_escape


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


def load_page(page):
    return gramex.cache.open(page, 'template', rel=True).generate(
        view_source=view_source,
        only_source=only_source
    )
