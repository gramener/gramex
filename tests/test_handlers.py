import json
import os
import requests
import pandas as pd
import gramex
import gramex.handlers
from . import server
from . import TestGramex
from orderedattrdict import AttrDict
from nose.tools import eq_, ok_, assert_raises
from tornado.web import create_signed_value
from urllib.request import urlopen
from urllib.error import HTTPError
from gramex.services import info
from gramex.http import OK, NOT_FOUND, INTERNAL_SERVER_ERROR, FORBIDDEN, TOO_MANY_REQUESTS


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

    def test_xsrf_ajax(self):
        # Requests sent with X-Requested-With should not need an XSRF cookie
        url = server.base_url + '/xsrf/yes'
        # Mangle case below to ensure Gramex handles it case-insensitively
        r = requests.post(url, headers={'X-Requested-With': 'xMlHtTpReQuESt'})
        eq_(r.status_code, OK)
        # fetch() sends a Sec-Fetch-Mode: cors
        r = requests.post(url, headers={'Sec-Fetch-Mode': 'cors'})
        eq_(r.status_code, OK)
        # <form> sends a Sec-Fetch-Mode of navigate in modern (desktop) browsers.
        # Older browsers do not send it.
        r = requests.post(url, headers={'Sec-Fetch-Mode': 'navigate'})
        eq_(r.status_code, FORBIDDEN)


class TestSetupErrors(TestGramex):
    def test_invalid_handler(self):
        self.check('/invalid-handler', code=NOT_FOUND)

    def test_invalid_setup(self):
        self.check(
            '/invalid-setup',
            code=INTERNAL_SERVER_ERROR,
            text='url:invalid-setup: needs "function:"',
        )

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
            ok_('\n' in text)  # error-404.json template has newlines
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
            ok_('\n' not in text)  # since whitespace=oneline
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
        self.check('/README.md', path='README.md', headers={'Cache-Control': 'max-age=60'})
        self.check('/sample.png', path='sample.png', headers={'Cache-Control': 'max-age=60'})

    def test_favicon(self):
        self.check(
            '/favicon.ico',
            path='../gramex/favicon.ico',
            headers={'Cache-Control': 'public, max-age=86400'},
        )


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
        eq_(r['url']['appconfig']['kwargs']['headers'], {'Content-Type': 'application/json'})


class TestRateLimit(TestGramex):
    def test_setup(self):
        def setup(ratelimit=None, ratelimit_app_conf=None, base=gramex.handlers.BaseHandler):
            '''Run setup_ratelimit() on a new subclass of cls'''
            class_vars = {
                'conf': AttrDict(pattern='/test'),
                'name': 'test',
                '_on_init_methods': [],
                '_on_finish_methods': [],
            }
            handler = type(base.__name__, (base,), class_vars)
            handler.setup_ratelimit(ratelimit, ratelimit_app_conf)
            return handler

        # ratelimit: is optional
        setup(None, None)

        # ratelimit: requires app.ratelimit
        with assert_raises(ValueError) as cm:
            setup({}, None)
        eq_(cm.exception.args[0], "url:test.ratelimit: no app.ratelimit defined")

        # ratelimit.keys required
        with assert_raises(ValueError) as cm:
            setup({}, {})
        eq_(cm.exception.args[0], 'url:test.ratelimit.keys: missing')

        # ratelimit.limit required
        with assert_raises(ValueError) as cm:
            setup({'keys': 'daily'}, {})
        eq_(cm.exception.args[0], 'url:test.ratelimit.limit: missing')

        # ratelimit.keys strings MUST be predefined
        with assert_raises(ValueError) as cm:
            setup({'keys': 'daily', 'limit': 5}, {})
        eq_(cm.exception.args[0], 'url:test.ratelimit.keys: daily is unknown')

        # ratelimit.keys strings MUST be str/list
        with assert_raises(ValueError) as cm:
            setup({'keys': 0, 'limit': 5}, {})
        eq_(cm.exception.args[0], 'url:test.ratelimit.keys: needs dict list, not 0')

        # ratelimit.keys: invalid function compilation directly raises exceptions, e.g. SyntaxError
        with assert_raises(SyntaxError):
            setup({'keys': [{'function': ';$@'}], 'limit': 5}, {})

        # ratelimit.keys dicts need a function:
        with assert_raises(ValueError) as cm:
            setup({'keys': {'x': 0}, 'limit': 5}, {})
        eq_(cm.exception.args[0], "url:test.ratelimit.keys: {'x': 0} has no function:")
        with assert_raises(ValueError) as cm:
            setup({'keys': [{'x': 0}], 'limit': 5}, {})
        eq_(cm.exception.args[0], "url:test.ratelimit.keys: {'x': 0} has no function:")

        # ratelimit.keys can be a predefined key string
        for key in ('hourly', 'daily', 'weekly', 'monthly', 'yearly', 'user'):
            ok_(setup({'keys': key, 'limit': 5}, gramex.conf.app.ratelimit)._ratelimit.store)

        # ratelimit.keys can be a dict with a function. Defines a single key
        ok_(setup({'keys': {'function': '0'}, 'limit': 5}, gramex.conf.app.ratelimit))

        # ratelimit.keys can be a comma-separated string
        cls = setup({'keys': 'daily, user', 'limit': 5}, gramex.conf.app.ratelimit)
        eq_(len(cls._ratelimit.key_fn), 2)

        # ratelimit.keys can be an array of strings
        cls = setup({'keys': ['daily', 'user'], 'limit': 5}, gramex.conf.app.ratelimit)
        eq_(len(cls._ratelimit.key_fn), 2)

        # ratelimit.limit must be a number
        with assert_raises(ValueError) as cm:
            setup({'keys': 'daily', 'limit': 'x'}, gramex.conf.app.ratelimit)
        eq_(cm.exception.args[0], "url:test.ratelimit.limit: needs {'function': number}, not x")

        # ratelimit.limit can be a function
        cls = setup({'keys': 'user', 'limit': {'function': '5'}}, gramex.conf.app.ratelimit)
        eq_(cls._ratelimit.limit_fn(None), 5)

        # EVERY handler supports rate-limiting via `ratelimit:`
        for base in (
            gramex.handlers.FunctionHandler,
            gramex.handlers.FormHandler,
            gramex.handlers.FileHandler,
            gramex.handlers.DriveHandler,
        ):
            cls = setup({'keys': 'daily, user', 'limit': 5}, gramex.conf.app.ratelimit, base)
            ok_(issubclass(cls, base))

        # ratelimit.keys return the expected values
        all_keys = ['hourly', 'daily', 'weekly', 'monthly', 'yearly', 'user']
        cls = setup({'keys': all_keys, 'limit': 5}, gramex.conf.app.ratelimit)
        key_fn = dict(zip(all_keys, cls._ratelimit.key_fn))
        handler = AttrDict(current_user=AttrDict(id='a@b'))
        eq_(key_fn['hourly']['function'](handler), pd.Timestamp.utcnow().strftime('%Y-%m-%d %H'))
        eq_(key_fn['daily']['function'](handler), pd.Timestamp.utcnow().strftime('%Y-%m-%d'))
        eq_(key_fn['weekly']['function'](handler), pd.Timestamp.utcnow().strftime('%Y %U'))
        eq_(key_fn['monthly']['function'](handler), pd.Timestamp.utcnow().strftime('%Y-%m'))
        eq_(key_fn['yearly']['function'](handler), pd.Timestamp.utcnow().strftime('%Y'))
        eq_(key_fn['user']['function'](handler), 'a@b')

    def test_ratelimit(self):
        def check(url, user, limit, remaining, code=OK):
            # If user= is specified, send an {'id': user} object via headers
            headers = {}
            if user is not None:
                cookie_secret = gramex.service.app.settings['cookie_secret']
                sign = create_signed_value(cookie_secret, 'user', json.dumps({'id': user}))
                headers['X-Gramex-User'] = sign

            # Check the status code and X-Ratelimit-* headers
            r = self.check(url, code=code, request_headers=headers)
            if code in (OK, TOO_MANY_REQUESTS):
                eq_(r.headers['X-Ratelimit-Limit'], str(limit))
                eq_(r.headers['X-Ratelimit-Remaining'], str(remaining))
                # Check expiry time to plus/minus 2 seconds.
                # NOTE: This test may fail if running exactly at UTC midnight
                eod = pd.Timestamp.utcnow().normalize() + pd.Timedelta(days=1)
                expiry = int((eod - pd.Timestamp.utcnow()).total_seconds())
                ok_(expiry - 2 <= int(r.headers['X-Ratelimit-Reset']) <= expiry + 2)
                # Retry-After header should be sent only for
                if code == TOO_MANY_REQUESTS:
                    eq_(r.headers['Retry-After'], r.headers['X-Ratelimit-Reset'])
                else:
                    ok_('Retry-After' not in r.headers)
            else:
                # No headers sent for HTTP errors
                ok_('X-Ratelimit-Limit' not in r.headers)
                ok_('X-Ratelimit-Remaining' not in r.headers)
                ok_('X-Ratelimit-Reset' not in r.headers)
                ok_('Retry-After' not in r.headers)

        # Reset usage count for all users before beginning the test
        self.check('/ratelimit/reset')
        self.check('/ratelimit/reset?user=alpha')
        self.check('/ratelimit/reset?user=beta')

        # All HTTP headers come through OK. First usage leaves us with 2 remaining
        check('/ratelimit/a', None, 3, 2)
        # /ratelimit/b uses the same pool as /a
        check('/ratelimit/b', None, 3, 1)
        # HTTP errors don't deduct from usage
        check('/ratelimit/a?n=0', None, 3, 1, INTERNAL_SERVER_ERROR)
        check('/ratelimit/b?n=0', None, 3, 1, INTERNAL_SERVER_ERROR)
        # When usage exceeds, we get HTTP 429
        check('/ratelimit/a', None, 3, 0)
        check('/ratelimit/a', None, 3, 0, TOO_MANY_REQUESTS)
        check('/ratelimit/b', None, 3, 0, TOO_MANY_REQUESTS)
        # Different users get a different limits
        check('/ratelimit/a', 'alpha', 3, 2)
        check('/ratelimit/a', 'beta', 3, 2)
        check('/ratelimit/b', 'alpha', 3, 1)
        check('/ratelimit/b', 'beta', 3, 1)
