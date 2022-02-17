import os
import requests
import shutil
import unittest
from lxml import etree      # nosec: lxml is safe   # noqa: F401 - other modules use this
from . import server
from nose.tools import eq_, ok_
from orderedattrdict import AttrDict
from pandas.testing import assert_frame_equal as afe   # noqa: F401 - other modules use this

tempfiles = AttrDict()
folder = os.path.dirname(os.path.abspath(__file__))


def setUp():
    # Remove uploads folder before Gramex locks .meta.h5
    upload_path = os.path.join(folder, 'uploads')
    if os.path.exists(upload_path):
        shutil.rmtree(upload_path)
    server.start_gramex()


def tearDown():
    server.stop_gramex()

    for filename in tempfiles.values():
        if os.path.exists(filename):
            os.unlink(filename)


def in_(a, b, msg=None):
    '''Is dict a a subset of dict b?'''
    ok_(a.items() <= b.items(), msg)


class TestGramex(unittest.TestCase):
    '''Base class to test Gramex running as a subprocess'''

    def get(self, url, session=None, method='get', timeout=10, **kwargs):
        req = session or requests
        return getattr(req, method)(server.base_url + url, timeout=timeout, **kwargs)

    def check(self, url, data=None, path=None, code=200, text=None, no_text=None,
              request_headers=None, headers=None, session=None, method='get', timeout=10):
        '''
        check(url) checks if the url returns the correct response. Parameters:

        :arg string url: Relative URL from test server base
        :arg dict data: optional data= to pass to requests.get/post
        :arg dict request_headers: options headers= to pass to requests.get/post
        :arg string method: HTTP method (default: 'get', may be 'post', etc.)
        :arg Session session: requests.Session object to use (default: ``requests``)
        :arg int timeout: seconds to wait (default: 10)

        :arg int code: returned status code must match this (default: 200)
        :arg string text: returned body must contain this text
        :arg string no_text: returned body must NOT contain this text
        :arg string path: returned body must equal the contents of the file at this path
        :arg dict headers: returned headers must contain these items. Value can be:
            - None/False: the header SHOULD NOT exist
            - True: the header SHOULD exist
            - string: the header must equal this string

        If any of the checks do not match, raises an assertion error.
        '''
        r = self.get(url, session=session, data=data, method=method, timeout=timeout,
                     headers=request_headers)
        eq_(r.status_code, code, '%s: code %d != %d' % (url, r.status_code, code))
        if text is not None:
            self.assertIn(text, r.text, '%s: %s not in %s' % (url, text, r.text))
        if no_text is not None:
            self.assertNotIn(text, r.text, '%s: %s should not be in %s' % (url, text, r.text))
        if path is not None:
            with (server.info.folder / path).open('rb') as file:
                eq_(r.content, file.read(), '%s != %s' % (url, path))
        if headers is not None:
            for header, value in headers.items():
                if value is None or value is False:
                    ok_(header not in r.headers, '%s: should not have header %s' % (url, header))
                elif value is True:
                    ok_(header in r.headers, '%s: should have header %s' % (url, header))
                else:
                    actual = r.headers[header]
                    eq_(actual, value, '%s: header %s = %s != %s' % (url, header, actual, value))
        return r

    def check_css(self, html, *selectors):
        '''
        Checks if a series of CSS selectors are present in the HTML. For example:

            self.check_css(html,
                ('h1', 'Admin'),              # first H1 is Admin
                ('h1', 'is', 'Admin'),        # first H1 has text Admin
                ('img', 'is', {'src': 'X'}),  # first img has src="X"
                ('h1', 1, 'X'},               # second H1 should have text X
                ('h1', -1, 'X'},              # last H1 should have text X
                ('h1', 'has', 'X'},           # any H1 should have text X
                ('h1', 'all', 'X'},           # all H1 should have text X
            )
        '''
        import re
        import lxml.html
        from lxml.cssselect import CSSSelector
        tree = lxml.html.fromstring(html)

        for selector in selectors:
            if len(selector) == 2:
                (css, val), how = selector, 'is'
            elif len(selector) == 3:
                css, how, val = selector
            else:
                raise ValueError('Selector %s must be a (css, how, val) triple' % selector)
            # Check all matching nodes. At least one node must exist
            nodes = CSSSelector(css)(tree)
            ok_(len(nodes) > 0, 'CSS %s missing' % css)

            # val must be a dict. Convert text values to dict. Raise error for rest
            if isinstance(val, str):
                val = {'@text': val}
            elif not isinstance(val, dict):
                raise ValueError('CSS %s has invalid value %s' % (css, val))

            for attr, v in val.items():
                if attr == '@text':
                    actuals = [node.text for node in nodes]
                else:
                    actuals = [node.get(attr, None) for node in nodes]

                # Try substring search. Else try regexp search
                regex = re.compile(v)
                match = lambda x: x in actual or regex.search(x)        # noqa

                # First or specified selector should match v
                if how == 'is' or isinstance(how, int):
                    actual = actuals[0 if how == 'is' else how]
                    if not match(actual):
                        self.fail('CSS %s@%s = %s != %s' % (css, attr, actual, v))
                # Any selector should match v
                elif how in {'has', 'any'}:
                    if not any(match(actual) for actual in actuals):
                        self.fail('CSS %s@%s has no %s' % (css, attr, v))
                # All selectors should match v
                elif how == 'all':
                    if not all(match(actual) for actual in actuals):
                        self.fail('CSS %s@%s is not all %s' % (css, attr, v))
                else:
                    raise ValueError('CSS %s: invalid how: "%s"' % (css, how))
        return tree


def remove_if_possible(target):
    '''
    os.remove(file).
    But ignore Windows antivirus software preventing deletion
    '''
    if not os.path.exists(target):
        return
    try:
        os.remove(target)
    except PermissionError:
        pass
