from __future__ import unicode_literals
import os
import json
import time
import shutil
import requests
import lxml.html
import pandas as pd
import sqlalchemy as sa
from orderedattrdict import AttrDict
from nose.plugins.skip import SkipTest
from six.moves.urllib_parse import urlencode
import gramex
import gramex.config
from gramex.http import OK, UNAUTHORIZED, FORBIDDEN, BAD_REQUEST
from . import TestGramex, server, tempfiles, utils

folder = os.path.dirname(os.path.abspath(__file__))


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

        # Test expiry date. It should be within a second of now, plus expiry date
        self.assertIn('_t', self.data1)
        diff = time.time() + gramex.conf.app.session.expiry * 24 * 60 * 60 - self.data1['_t']
        self.assertLess(abs(diff), 0.2)

        # Test persistence under graceful shutdown
        server.stop_gramex()
        server.start_gramex()
        r1 = self.session1.get(self.url)
        self.assertEqual(self.data1, r1.json())
        self.assertEqual(self.data1['var'], 'x')
        r2 = self.session2.get(self.url)
        self.assertEqual(self.data2, r2.json())

    def test_cookies(self):
        r = requests.get(self.url + '?var=x')
        cookies = {c.name: c for c in r.cookies}
        self.assertIn('sid', cookies)
        self.assertIn('httponly', cookies['sid']._rest)
        # HTTP requests should not have a secure flag
        self.assertNotIn('secure', cookies['sid']._rest)
        # TODO: HTTPS requests SHOULD have a secure flag


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

    def login(self, user, password, query_next=None, header_next=None, headers={}):
        params = self.redirect_kwargs(query_next, header_next)
        r = self.session.get(self.url, **params)
        tree = lxml.html.fromstring(r.text)
        self.assertEqual(tree.xpath('.//h1')[0].text, 'Auth')

        # Create form submission data
        data = {'user': user, 'password': password}
        data['xsrf'] = tree.xpath('.//input[@name="_xsrf"]')[0].get('value')

        # Submitting the correct password redirects
        if headers is not None:
            params['headers'].update(headers)
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
        old_sid = self.session.cookies['sid']
        self.login_ok('beta', 'beta', check_next='/dir/index/')
        new_sid = self.session.cookies['sid']
        # Test session fixation: login changes sid
        self.assertNotEqual(old_sid, new_sid)

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


class LoginFailureMixin(object):
    def test_slow_down_attacks(self):
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        t0 = time.time()
        # Second failure: delay of about 0.2 seconds
        self.unauthorized('alpha', 'wrong')
        t1 = time.time()
        self.assertTrue(0.3 >= t1 - t0 >= 0.2)
        # Third failure: delay of about 0.4 seconds
        self.unauthorized('alpha', 'wrong')
        t2 = time.time()
        self.assertTrue(0.5 >= t2 - t1 >= 0.4)
        # Successful login is instantaneous
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        t3 = time.time()
        self.assertTrue(t3 - t2 < 0.2)


class TestSimpleAuth(AuthBase, LoginMixin, LoginFailureMixin):
    # Just apply LoginMixin tests to AuthBase
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/simple'

    # Run additional tests for session and login features
    def get_session(self, headers=None):
        return self.session.get(server.base_url + '/auth/session', headers=headers).json()

    def test_login_action(self):
        self.login('alpha', 'alpha')
        self.assertDictContainsSubset({'action_set': True}, self.get_session())

    def test_attributes(self):
        self.login('gamma', 'gamma')
        self.assertEquals({'user': 'gamma', 'id': 'gamma', 'role': 'user', 'password': 'gamma'},
                          self.get_session()['user'])

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
        # log into second session
        self.session = session2
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        self.assertEquals({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])
        # first session should be logged out now
        self.session = session1
        self.assertTrue('user' not in self.get_session())

    def test_override(self):
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        self.assertEquals({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import padding
        from base64 import b64encode
        public_key_text = open(os.path.join(folder, 'id_rsa.pub.pem'), 'rb').read()
        public_key = serialization.load_pem_public_key(public_key_text, backend=default_backend())
        result = {'user': 'override', 'role': 'admin'}
        pad = padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None)
        message = public_key.encrypt(json.dumps(result), pad)
        session_data = self.get_session(headers={'X-Gramex-User': b64encode(message)})
        self.assertEquals(result, session_data['user'])

    def test_otp(self):
        self.session = requests.Session()
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        otp1 = self.session.get(server.base_url + '/auth/otp?expire=10').json()
        otp2 = self.session.get(server.base_url + '/auth/otp?expire=10').json()
        otp_dead = self.session.get(server.base_url + '/auth/otp?expire=0').json()
        self.assertEquals({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])

        self.session = requests.Session()
        self.assertTrue('user' not in self.get_session())
        session_data = self.get_session(headers={'X-Gramex-OTP': otp1})
        self.assertEquals({'user': 'alpha', 'id': 'alpha'}, session_data['user'])

        self.session = requests.Session()
        self.assertTrue('user' not in self.get_session())
        session_data = self.session.get(server.base_url + '/auth/session',
                                        params={'gramex-otp': otp2}).json()
        self.assertEquals({'user': 'alpha', 'id': 'alpha'}, session_data['user'])

        self.session = requests.Session()
        for otp in [otp1, otp2, otp_dead, 'nan']:
            r = self.session.get(server.base_url + '/auth/session', headers={'X-Gramex-OTP': otp})
            self.assertEqual(r.status_code, BAD_REQUEST)
            r = self.session.get(server.base_url + '/auth/session', params={'gramex-otp': otp})
            self.assertEqual(r.status_code, BAD_REQUEST)


class TestAuthTemplate(TestGramex):
    def test_change_template(self):
        tempfiles.auth_template = auth_file = os.path.join(folder, 'authtemplate.html')
        shutil.copyfile(os.path.join(folder, 'auth.html'), auth_file)
        self.check('/auth/template', text='<h1>Auth</h1>')
        shutil.copyfile(os.path.join(folder, 'auth2.html'), auth_file)
        self.check('/auth/template', text='<h1>Auth 2</h1>')


class DBAuthBase(AuthBase, LoginFailureMixin):
    @staticmethod
    def create_database():
        data = pd.read_csv(os.path.join(folder, 'userdata.csv'), encoding='cp1252')
        data['password'] = data['password'] + data['salt']
        dburl = 'mysql+pymysql://root@%s/' % gramex.config.variables.MYSQL_SERVER
        # sqlalchemy needs encoding to be a `str` in both Python 2.x and 3.x
        encoding = str('utf-8')
        engine = sa.create_engine(dburl, encoding=encoding)
        try:
            engine.execute('DROP DATABASE IF EXISTS test_auth')
            engine.execute('CREATE DATABASE test_auth')
            engine.dispose()
            engine = sa.create_engine(dburl + 'test_auth', encoding=encoding)
            data.to_sql('users', con=engine, index=False)
        except sa.exc.OperationalError:
            raise SkipTest('Unable to connect to %s' % dburl)

    @classmethod
    def setUpClass(cls):
        super(DBAuthBase, cls).setUpClass()
        cls.create_database()
        cls.url = server.base_url + '/auth/db'


class TestDBAuth(DBAuthBase, LoginMixin):
    # Just apply LoginMixin tests to DBAuthBase
    def test_salt(self):
        self.unauthorized('epsilon', 'epsilon')
        self.login_ok('epsilon', 'epsilon', headers={'salt': 'abc'}, check_next='/dir/index/')
        self.unauthorized('alpha', 'alpha', headers={'salt': 'abc'})
        self.login_ok('alpha', 'alpha', headers={'salt': '123'}, check_next='/dir/index/')


class TestAuthorize(DBAuthBase):
    def initialize(self, url, user='alpha', login_url='/login/'):
        self.session = requests.Session()
        r = self.session.get(server.base_url + url)
        self.assertEqual(r.url, server.base_url + login_url + '?' + urlencode({'next': url}))
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

    def test_auth_membership(self, url='/auth/membership'):
        self.initialize(url)
        self.check(url, path='dir/alpha.txt', session=self.session)
        self.login_ok('beta', 'beta', check_next='/dir/index/')
        self.check(url, path='dir/alpha.txt', session=self.session)
        self.login_ok('gamma', 'gamma', check_next='/dir/index/')
        self.check(url, code=FORBIDDEN, session=self.session)

    def test_auth_memberships(self):
        # Same as test_auth_membership, but on a different URL
        self.test_auth_membership('/auth/memberships')

    def test_auth_condition(self):
        self.initialize('/auth/condition', user='beta')
        self.check('/auth/condition', path='dir/alpha.txt', session=self.session)
        self.login_ok('delta', 'delta', check_next='/dir/index/')
        self.check('/auth/condition', path='dir/alpha.txt', session=self.session)
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        self.check('/auth/condition', code=FORBIDDEN, session=self.session)

    def test_auth_login_url(self):
        self.initialize('/auth/login-url', login_url='/auth/simple')

    def test_auth_template(self):
        self.initialize('/auth/unauthorized-template', user='alpha')
        self.check('/auth/unauthorized-template', code=FORBIDDEN, text='403-template', session=self.session)
        self.initialize('/auth/unauthorized-template', user='beta')
        self.check('/auth/unauthorized-template', path='dir/alpha.txt', session=self.session)
