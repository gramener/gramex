import os
import requests
from . import server
from . import TestGramex
from nose.tools import eq_, ok_
from six.moves.urllib_request import urlopen
from six.moves.urllib_error import HTTPError
from gramex.services import info
from gramex.http import OK, NOT_FOUND, INTERNAL_SERVER_ERROR, FORBIDDEN


class TestURLPriority(TestGramex):
    # Test Gramex URL priority sequence

    def test_url_priority(self):
        self.check('/path/abc', text='/path/.*')
        self.check('/path/file', text='/path/file')
        self.check('/path/dir', text='/path/.*')
        self.check('/path/dir/', text='/path/dir/.*')
        self.check('/path/dir/abc', text='/path/dir/.*')
        self.check('/path/dir/file', text='/path/dir/file')
        self.check('/path/priority', text='/path/priority')


class TestURLNormalization(TestGramex):
    # Test URL pattern normalization

    def test_url_normalization(self):
        self.check('/path/norm1', text='/path/norm1')
        self.check('/path/norm2', text='/path/norm2')


class TestAttributes(TestGramex):
    # Ensure that BaseHandler subclasses have relevant attributes

    def test_attributes(self):
        self.check('/func/attributes', code=OK)


class TestXSRF(TestGramex):
    # Test BaseHandler xsrf: setting

    def test_xsrf(self):
        r = self.check('/path/norm')
        ok_('Set-Cookie' not in r.headers)

        # First request sets xsrf cookie
        session = requests.Session()
        r = session.get(server.base_url + '/xsrf', timeout=10)
        ok_('Set-Cookie' in r.headers)
        ok_('_xsrf' in r.headers['Set-Cookie'])

        # Next request does not set xsrf cookie, because it already exists
        r = session.get(server.base_url + '/xsrf', timeout=10)
        ok_('Set-Cookie' not in r.headers)

    def test_xsrf_false(self):
        # When xsrf_cookies is set to False, POST works
        r = requests.post(server.base_url + '/xsrf/no')
        eq_(r.status_code, OK)

    def test_xsrf_true(self):
        # When xsrf_cookies is set to True, POST fails without _xsrf
        r = requests.post(server.base_url + '/xsrf/yes')
        eq_(r.status_code, FORBIDDEN)

    def test_ajax(self):
        # Requests sent with X-Requested-With should not need an XSRF cookie
        r = requests.post(server.base_url + '/xsrf/yes', headers={
            # Mangle case below to ensure Gramex handles it case-insensitively
            'X-Requested-With': 'xMlHtTpReQuESt',
        })
        eq_(r.status_code, OK)


class TestSetupErrors(TestGramex):
    def test_invalid_handler(self):
        self.check('/invalid-handler', code=NOT_FOUND)

    def test_invalid_setup(self):
        self.check('/invalid-setup', code=INTERNAL_SERVER_ERROR,
                   text='url: invalid-setup: No function in conf {}')

    def test_invalid_function(self):
        self.check('/invalid-function', code=INTERNAL_SERVER_ERROR, text='nonexistent')


class TestErrorHandling(TestGramex):
    # Test BaseHandler error: setting
    def test_404_escaped(self):
        # Check that templates are HTML escaped by default
        try:
            # Requests converts <script> into %3Cscript%3E before sending URL.
            # So use urlopen instead of requests.get
            urlopen(server.base_url + '/error/404-escaped-<script>')
        except HTTPError as err:
            eq_(err.code, NOT_FOUND)
            text = err.read().decode('utf-8')
            ok_(' &quot;/error/404-escaped-&lt;script&gt;&quot;' in text)
            ok_('\n' in text)   # error-404.json template has newlines
        else:
            ok_(False, '/error/404-escaped-<script> should raise a 404')

    def test_404_unescaped(self):
        # autoescape can be over-ridden
        try:
            urlopen(server.base_url + '/error/404-template-<script>')
        except HTTPError as err:
            eq_(err.code, NOT_FOUND)
            text = err.read().decode('utf-8')
            ok_(' "/error/404-template-<script>' in text)
            ok_('\n' not in text)   # since whitespace=oneline
        else:
            ok_(False, '/error/404-template-<script> should raise a 404')

    def test_500(self):
        r = self.check('/error/500-function', code=INTERNAL_SERVER_ERROR)
        eq_(r.headers['Content-Type'], 'application/json')
        result = r.json()
        eq_(result['status_code'], INTERNAL_SERVER_ERROR)
        ok_(result['handler.request.uri'].endswith('/error/500-function'))


class TestMime(TestGramex):
    def setUp(self):
        self.mime_map = {
            '.yml': 'text/yaml; charset=UTF-8',
            # ToDo: Fix with FileHandler 2
            # '.yaml': 'text/yaml; charset=UTF-8',
            '.md': 'text/markdown; charset=UTF-8',
            '.markdown': 'text/markdown; charset=UTF-8',
            '.json': 'application/json',
            '.svg': 'image/svg+xml',
            # '.py': 'text/plain; charset=UTF-8',       # .py files are forbidden by default
            '.h5': 'application/x-hdf5',
            '.hdf5': 'application/x-hdf5',
        }
        self.files = set()
        folder = os.path.dirname(os.path.abspath(__file__))
        for ext, mime in self.mime_map.items():
            path = os.path.join(folder, 'dir', 'gen' + ext)
            self.files.add(path)
            with open(path, 'wb'):
                pass

    def test_mime(self):
        for ext, mime in self.mime_map.items():
            r = self.check('/dir/gen' + ext)
            eq_(r.headers['Content-Type'], mime)

    def tearDown(self):
        for file in self.files:
            os.unlink(file)


class TestBaseHandler(TestGramex):
    def test_headers(self):
        self.check('/', headers={'X-BaseHandler': 'base'})

    def test_kwargs(self):
        # Fetch {name: handler_class} for Tornado 5.0 onwards
        classes = {
            rule.handler_class.name: rule.handler_class
            for rules in info.app.default_router.rules
            for rule in rules.target.rules
        }
        # FileHandler inherits kwargs from handlers.FileHandler and handlers.BaseHandler
        cls = classes['base']
        eq_(cls.name, 'base')
        eq_(cls.kwargs['path'], 'dir/index.html')
        headers = cls.kwargs['headers']
        eq_(headers['X-BaseHandler'], 'base')
        eq_(headers['X-BaseHandler'], 'base')
        eq_(headers['X-FileHandler'], 'base')
        eq_(headers['X-FileHandler-Base'], 'base')


class TestDefaultGramexYAML(TestGramex):
    def test_default_files(self):
        # Default gramex.yaml FileHandler exposes files in the current directory
        self.check('/README.md', path='README.md', headers={
            'Cache-Control': 'max-age=60'
        })
        self.check('/sample.png', path='sample.png', headers={
            'Cache-Control': 'max-age=60'
        })

    def test_favicon(self):
        self.check('/favicon.ico', path='../gramex/favicon.ico', headers={
            'Cache-Control': 'public, max-age=86400'
        })


class TestAlias(TestGramex):
    def test_alias(self):
        # gramex.service uses service: as an alias for handler.
        # It also creates alternate names for these services.
        # Just check a few. If some work, all should work.
        self.check('/alias-command')
        self.check('/alias-data')
        self.check('/alias-function')


class TestConfig(TestGramex):
    def test_appconfig(self):
        # gramex.appconfig should contain the current app configuration
        r = self.check('/appconfig').json()
        eq_(r['url']['appconfig']['pattern'], '/appconfig')
        eq_(r['url']['appconfig']['kwargs']['headers'], {
            'Content-Type': 'application/json'
        })
