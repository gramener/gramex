import ast
import gramex
import pandas as pd
from . import server
from nose.tools import ok_, eq_
from .test_auth import AuthBase
from gramex.http import FORBIDDEN
from websocket import create_connection


class TestAdmin(AuthBase):
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/simple'

    def test_default(self):
        r = self.check('/admin/default/')
        self.check_css(
            r.text,
            ('title', 'Admin'),
            ('link', {'href': 'ui/bootstraptheme.css'}),
            ('h3', 'has', 'Users'),
            ('h3', 'has', 'Shell'),
            ('h3', 'has', 'Info'),
            ('h3', 'has', 'Config'),
            ('h3', 'has', 'Logs'),
        )

    def test_kwargs(self):
        r = self.check('/admin/kwargs/')
        self.check_css(
            r.text,
            ('title', 'Custom title'),
            ('link', {'href': 'ui/bootstraptheme.css?font-family-base=roboto'}),
            ('.navbar-brand img', {'src': 'logo.png'}),
            ('h3', 'has', 'Users'),
            ('h3', 'has', 'Shell'),
            ('h3', 'has', 'Info'),
        )

    def test_auth(self):
        # Non-logged-in users redirected to login page
        r = self.check('/admin/auth/', session=self.session)
        self.check_css(r.text, ('h1', 'Auth'))
        # Logged-in users can see the page
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        r = self.check('/admin/auth/', session=self.session)
        self.check_css(r.text, ('title', 'Admin'))
        # Wrong users cannot see the page
        self.login_ok('beta', 'beta', check_next='/dir/index/')
        self.check('/admin/auth/', code=FORBIDDEN, session=self.session)

    def test_info(self):
        self.check('/admin/default/?tab=info')
        result = self.check('/admin/default/info').json()
        ok_(isinstance(result, list))
        data = pd.DataFrame(result).set_index(['section', 'key'])
        index = data.index
        ok_(data['value']['python', 'path'])
        ok_(data['value']['python', 'version'])
        eq_(data['value']['gramex', 'version'], gramex.__version__)
        ok_(data['value']['gramex', 'path'])
        ok_(('gramex', 'memory-usage') in index)
        ok_(('gramex', 'open-files') in index)
        ok_(('system', 'cpu-count') in index)
        ok_(('system', 'cpu-usage') in index)
        ok_(('system', 'disk-usage') in index)
        ok_(('system', 'memory-usage') in index)
        ok_(('node', 'version') in index)
        ok_(('node', 'path') in index)
        ok_(('npm', 'version') in index)
        ok_(('yarn', 'version') in index)
        ok_(('git', 'version') in index)
        ok_(('git', 'path') in index)

    def test_users(self):
        self.check('/admin/default/?tab=users')
        # TODO: add tests

    def test_shell(self):
        self.check('/admin/default/?tab=shell')
        ws_url = server.base_url.replace('http://', 'ws://') + '/admin/default/webshell'
        ws = create_connection(ws_url)
        # Python expressions are computed
        ws.send('1 + 2')
        eq_(ws.recv(), '3')
        # Session state is maintained. Gramex can be imported
        ws.send('import gramex')
        eq_(ws.recv(), '')
        ws.send('gramex.__version__')
        eq_(ast.literal_eval(ws.recv()), gramex.__version__)
        # handler is available for use
        ws.send('handler.session')
        result = ast.literal_eval(ws.recv())
        ok_('_t' in result and 'id' in result)
