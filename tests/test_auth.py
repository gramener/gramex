from __future__ import unicode_literals
import os
import json
import requests
import lxml.html
import pandas as pd
import sqlalchemy as sa
from nose.plugins.skip import SkipTest
from six.moves.urllib_parse import urlencode
import gramex.config
from gramex.http import OK, UNAUTHORIZED, FORBIDDEN
from . import TestGramex
from . import server


class TestSession(TestGramex):
    @classmethod
    def setupClass(cls):
        cls.session1 = requests.Session()
        cls.session2 = requests.Session()
        cls.url = server.base_url + '/auth/session'

    def test_session(self):
        r1 = self.session1.get(self.url + '?var=x')
        self.assertIn('sid', r1.cookies)
        self.data1 = json.loads(r1.text)
        self.assertIn('id', self.data1)
        self.assertEqual(self.data1['var'], 'x')

        r2 = self.session2.get(self.url)
        self.assertIn('sid', r2.cookies)
        self.data2 = json.loads(r2.text)
        self.assertIn('id', self.data2)
        self.assertNotIn('var', self.data2)

        self.assertNotEqual(r1.cookies['sid'], r2.cookies['sid'])
        self.assertNotEqual(self.data1['id'], self.data2['id'])

        # Test persistence under graceful shutdown
        server.stop_gramex()
        server.start_gramex()
        r1 = self.session1.get(self.url)
        self.assertEqual(self.data1, json.loads(r1.text))
        self.assertEqual(self.data1['var'], 'x')
        r2 = self.session2.get(self.url)
        self.assertEqual(self.data2, json.loads(r2.text))


class AuthBase(TestGramex):
    @classmethod
    def setUpClass(cls):
        cls.session = requests.Session()

    @staticmethod
    def redirect_kwargs(query_next, header_next):
        # Get the login page
        params, headers = {}, {}
        if query_next is not None:
            params['next'] = query_next
        if header_next is not None:
            headers['NEXT'] = header_next
        return {'params': params, 'headers': headers}

    def login(self, user, password, query_next=None, header_next=None):
        params = self.redirect_kwargs(query_next, header_next)
        r = self.session.get(self.url, **params)
        tree = lxml.html.fromstring(r.text)
        self.assertEqual(tree.xpath('.//h1')[0].text, 'Auth')

        # Create form submission data
        data = {'user': user, 'password': password}
        data['xsrf'] = tree.xpath('.//input[@name="_xsrf"]')[0].get('value')

        # Submitting the correct password redirects
        return self.session.post(self.url, timeout=10, data=data, headers=params['headers'])

    def logout(self, query_next=None, header_next=None):
        url = server.base_url + '/auth/logout'
        return self.session.get(url, timeout=10, **self.redirect_kwargs(query_next, header_next))

    def login_ok(self, *args, **kwargs):
        check_next = kwargs.pop('check_next')
        r = self.login(*args, **kwargs)
        self.assertEqual(r.status_code, OK)
        self.assertNotRegexpMatches(r.text, 'error code')
        self.assertEqual(r.url, server.base_url + check_next)

    def logout_ok(self, *args, **kwargs):
        check_next = kwargs.pop('check_next')
        # logout() does not accept user, password. So Just pass the kwargs
        r = self.logout(**kwargs)
        self.assertEqual(r.status_code, OK)
        self.assertEqual(r.url, server.base_url + check_next)

    def unauthorized(self, *args, **kwargs):
        r = self.login(*args, **kwargs)
        self.assertEqual(r.status_code, UNAUTHORIZED)
        self.assertRegexpMatches(r.text, 'error code')
        self.assertEqual(r.url, self.url)


class LoginMixin(object):
    def test_login(self):
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        self.login_ok('beta', 'beta', check_next='/dir/index/')

    def test_login_wrong_password(self):
        self.unauthorized('alpha', 'beta')

    def test_login_nonexistent_user(self):
        self.unauthorized('nonexistent', 'beta')

    def test_redirect(self):
        for method in [self.login_ok, self.logout_ok]:
            method('alpha', 'alpha', query_next='/func/args', check_next='/func/args')
            method('alpha', 'alpha', header_next='/func/args', check_next='/func/args')

    def test_internal_redirect(self):
        # Passing a full HTTP URL that matches the local host still works
        url = server.base_url + '/func/args'
        for method in [self.login_ok, self.logout_ok]:
            method('alpha', 'alpha', query_next=url, check_next='/func/args')
            method('alpha', 'alpha', header_next=url, check_next='/func/args')

    def test_external_redirect(self):
        # When redirecting to an external URL or new port fall back to the default url: specified
        for external in ['https://gramener.com/', server.base_url.rsplit(':', 1)[0] + ':1234']:
            for method in [self.login_ok, self.logout_ok]:
                method('alpha', 'alpha', query_next=external, check_next='/dir/index/')
                method('alpha', 'alpha', header_next=external, check_next='/dir/index/')


class TestSimpleAuth(AuthBase, LoginMixin):
    # Just apply LoginMixin tests to AuthBase
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/simple'

    # Run additional tests for session and login features
    def get_session(self):
        return self.session.get(server.base_url + '/auth/session').json()

    def test_login_action(self):
        self.login('alpha', 'alpha')
        self.assertDictContainsSubset({'action_set': True}, self.get_session())

    def test_logout_action(self):
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        self.assertEquals({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])
        self.logout_ok(check_next='/dir/index/')
        self.assertTrue('user' not in self.get_session())

    def test_ensure_single_session(self):
        session1, session2 = requests.Session(), requests.Session()
        # log into first session
        self.session = session1
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        self.assertEquals({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])
        # log into second sessioj
        self.session = session2
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        self.assertEquals({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])
        # first session should be logged out now
        self.session = session1
        self.assertTrue('user' not in self.get_session())


class DBAuthBase(AuthBase):
    @classmethod
    def setUpClass(cls):
        super(DBAuthBase, cls).setUpClass()
        folder = os.path.dirname(os.path.abspath(__file__))
        cls.data = pd.read_csv(os.path.join(folder, 'userdata.csv'), encoding='cp1252')
        cls.dburl = 'mysql+pymysql://root@%s/' % gramex.config.variables.MYSQL_SERVER
        # sqlalchemy needs encoding to be a `str` in both Python 2.x and 3.x
        encoding = str('utf-8')
        cls.engine = sa.create_engine(cls.dburl, encoding=encoding)
        try:
            cls.engine.execute('DROP DATABASE IF EXISTS test_auth')
            cls.engine.execute('CREATE DATABASE test_auth')
            cls.engine.dispose()
            cls.engine = sa.create_engine(cls.dburl + 'test_auth', encoding=encoding)
            cls.data.to_sql('users', con=cls.engine, index=False)
        except sa.exc.OperationalError:
            raise SkipTest('Unable to connect to %s' % cls.dburl)
        cls.url = server.base_url + '/auth/db'


class TestDBAuth(DBAuthBase, LoginMixin):
    # Just apply LoginMixin tests to DBAuthBase
    pass


class TestAuthorize(DBAuthBase):
    def initialize(self, url, user='alpha'):
        self.session = requests.Session()
        r = self.session.get(server.base_url + url)
        self.assertEqual(r.url, server.base_url + '/login?' + urlencode({'next': url}))
        r = self.session.post(server.base_url + url)
        self.assertEqual(r.url, server.base_url + url)
        self.assertEqual(r.status_code, UNAUTHORIZED)
        self.login_ok(user, user, check_next='/dir/index/')

    def test_auth_filehandler(self):
        self.initialize('/auth/filehandler')
        self.check('/auth/filehandler', path='dir/alpha.txt', session=self.session)

    def test_auth_functionhandler(self):
        self.initialize('/auth/functionhandler')
        self.check('/auth/functionhandler', text='OK', session=self.session)

    def test_auth_datahandler(self):
        self.initialize('/auth/datahandler')

    def test_auth_jsonhandler(self):
        self.initialize('/auth/jsonhandler/')
        r = self.check('/auth/jsonhandler/', session=self.session)
        self.assertEqual(r.json(), {'x': 1})

    def test_auth_processhandler(self):
        self.initialize('/auth/processhandler')

    def test_auth_twitterresthandler(self):
        self.initialize('/auth/twitterresthandler')

    def test_auth_uploadhandler(self):
        self.initialize('/auth/uploadhandler')

    def test_auth_membership(self):
        self.initialize('/auth/membership')
        self.check('/auth/membership', path='dir/alpha.txt', session=self.session)
        self.login_ok('beta', 'beta', check_next='/dir/index/')
        self.check('/auth/membership', path='dir/alpha.txt', session=self.session)
        self.login_ok('gamma', 'gamma', check_next='/dir/index/')
        self.check('/auth/membership', code=FORBIDDEN, session=self.session)

    def test_auth_condition(self):
        self.initialize('/auth/condition', user='beta')
        self.check('/auth/condition', path='dir/alpha.txt', session=self.session)
        self.login_ok('delta', 'delta', check_next='/dir/index/')
        self.check('/auth/condition', path='dir/alpha.txt', session=self.session)
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        self.check('/auth/condition', code=FORBIDDEN, session=self.session)
