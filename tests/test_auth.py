import os
import json
import time
import email
import shutil
import requests
import lxml.html
import pandas as pd
import sqlalchemy as sa
from nose.tools import eq_, ok_, assert_not_equal as neq_
from nose.plugins.skip import SkipTest
from tornado.web import create_signed_value
from urllib.parse import urlencode, urljoin
import gramex
import gramex.config
from gramex.cache import SQLiteStore
from gramex.handlers.authhandler import _user_info_path
from gramex.http import OK, UNAUTHORIZED, FORBIDDEN, BAD_REQUEST
from . import TestGramex, server, tempfiles, dbutils, in_

folder = os.path.dirname(os.path.abspath(__file__))


class TestSession(TestGramex):
    @classmethod
    def setupClass(cls):
        cls.session1 = requests.Session()
        cls.session2 = requests.Session()
        cls.url = server.base_url + '/auth/session'

    def test_session(self):
        r1 = self.session1.get(self.url + '?var=x')
        self.assertIn('sid2', r1.cookies)
        self.data1 = json.loads(r1.text)
        self.assertIn('id', self.data1)
        eq_(self.data1['var'], 'x')

        r2 = self.session2.get(self.url)
        self.assertIn('sid2', r2.cookies)
        self.data2 = json.loads(r2.text)
        self.assertIn('id', self.data2)
        self.assertNotIn('var', self.data2)

        self.assertNotEqual(r1.cookies['sid2'], r2.cookies['sid2'])
        self.assertNotEqual(self.data1['id'], self.data2['id'])

        # Test expiry date. It should be within a few seconds of now, plus expiry date
        self.assertIn('_t', self.data1)
        diff = time.time() + gramex.conf.app.session.expiry * 24 * 60 * 60 - self.data1['_t']
        self.assertLess(abs(diff), 3)

        # Test persistence under graceful shutdown
        server.stop_gramex()
        server.start_gramex()
        r1 = self.session1.get(self.url)
        eq_(self.data1, r1.json())
        eq_(self.data1['var'], 'x')
        r2 = self.session2.get(self.url)
        eq_(self.data2, r2.json())

    def test_cookies(self):
        r = requests.get(self.url + '?var=x')
        cookies = {c.name: c for c in r.cookies}
        cookie = r.headers['Set-Cookie'].lower()
        self.assertIn('sid2', cookies)
        self.assertIn('httponly', cookie)
        self.assertIn('samesite=strict', cookie)
        self.assertIn('domain=.localhost.local', cookie)
        # HTTP requests should not have a secure flag
        # TODO: HTTPS requests SHOULD have a secure flag
        self.assertNotIn('secure', cookie)


class AuthBase(TestGramex):
    @classmethod
    def setUpClass(cls):
        cls.session = requests.Session()
        cls.LOGIN_TIMEOUT = 10

    @staticmethod
    def redirect_kwargs(query_next, header_next, referer=None):
        # Get the login page
        params, headers = {}, {}
        if query_next is not None:
            params['next'] = query_next
        if header_next is not None:
            headers['NEXT'] = header_next
        if referer is not None:
            headers['Referer'] = referer
        return {'params': params, 'headers': headers}

    def login(self, user, password, query_next=None, header_next=None, referer=None,
              headers={}, post_args={}):
        params = self.redirect_kwargs(query_next, header_next, referer=referer)
        r = self.session.get(self.url, **params)
        tree = self.check_css(r.text, ('h1', 'Auth'))

        # Create form submission data
        data = {'user': user, 'password': password}
        data['_xsrf'] = tree.xpath('.//input[@name="_xsrf"]')[0].get('value')
        data.update(post_args)

        # Submitting the correct password redirects
        if headers is not None:
            params['headers'].update(headers)
        return self.session.post(self.url, timeout=self.LOGIN_TIMEOUT,
                                 data=data, headers=params['headers'])

    def logout(self, query_next=None, header_next=None):
        url = server.base_url + '/auth/logout'
        return self.session.get(url, timeout=10, **self.redirect_kwargs(query_next, header_next))

    def login_ok(self, *args, **kwargs):
        check_next = kwargs.pop('check_next')
        r = self.login(*args, **kwargs)
        eq_(r.status_code, OK)
        self.assertNotRegexpMatches(r.text, 'error code')
        eq_(r.url, urljoin(server.base_url, check_next))

    def logout_ok(self, *args, **kwargs):
        check_next = kwargs.pop('check_next')
        # logout() does not accept user, password. So Just pass the kwargs
        r = self.logout(**kwargs)
        eq_(r.status_code, OK)
        eq_(r.url, urljoin(server.base_url, check_next))

    def unauthorized(self, *args, **kwargs):
        r = self.login(*args, **kwargs)
        eq_(r.status_code, UNAUTHORIZED)
        self.assertRegexpMatches(r.text, 'error code')
        eq_(r.url, self.url)

    def check_direct_post_redirect(self, *mapping):
        # If we call the POST method WITHOUT calling the GET, the redirect still works
        for kwargs, url in mapping:
            session = requests.Session()
            r = session.get(server.base_url + '/xsrf')
            data = {'user': 'alpha', 'password': 'alpha', '_xsrf': r.cookies['_xsrf']}
            if 'data' in kwargs:
                data.update(kwargs.pop('data'))
            r = session.post(self.url, data=data, allow_redirects=False, **kwargs)
            eq_(urljoin(server.base_url, r.headers['Location']), urljoin(server.base_url, url))


class LoginMixin(object):
    def test_login(self):
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        old_sid = self.session.cookies['sid2']
        self.login_ok('beta', 'beta', check_next='/dir/index/')
        new_sid = self.session.cookies['sid2']
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

    def test_post_redirect(self):
        # If we call the POST method WITHOUT calling the GET, all auth handlers
        # use ?next= and the NEXT header for redirection
        self.check_direct_post_redirect(
            ({}, '/dir/index/'),
            ({'headers': {'NEXT': '/header'}}, '/header'),
            ({'data': {'next': '/query'}}, '/query'),
            ({'headers': {'NEXT': '/header'}, 'data': {'next': '/query'}}, '/query'))


class LoginFailureMixin(object):
    def check_delay(self, start, min=None, max=None):
        t = time.time()
        # Give a 0.1s buffer in case of timing delays
        buffer = 0.1
        if min is not None and min > 0:
            self.assertGreaterEqual(t - start, min - buffer)
        if max is not None and max > 0:
            self.assertLessEqual(t - start, max + buffer)
        return t

    def test_slow_down_attacks(self, retries=3):
        # gramex.yaml configures the delays as [0.4, 0.8]. Test this
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        t0 = time.time()
        # First failure: delay of at least 0.2 seconds
        self.unauthorized('alpha', 'wrong')
        t1 = self.check_delay(t0, min=0.4)
        # Second failure: delay of at least 0.4 seconds
        self.unauthorized('alpha', 'wrong')
        self.check_delay(t1, min=0.8)
        # Successful login is instantaneous, even after a wrong attempt.
        # (But retry a few times, in case the system is slow.)
        for x in range(retries):
            t = time.time()
            self.login_ok('alpha', 'alpha', check_next='/dir/index/')
            try:
                self.check_delay(t, max=0.4)
                break
            except AssertionError:
                pass
        else:
            self.check_delay(t, max=0.4)


class TestSimpleAuth(AuthBase, LoginMixin, LoginFailureMixin):
    # Just apply LoginMixin tests to AuthBase
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/simple'

    # Run additional tests for session and login features
    def get_session(self, headers=None, params={}):
        return self.session.get(server.base_url + '/auth/session',
                                headers=headers, params=params).json()

    def test_login_action(self):
        self.login('alpha', 'alpha')
        self.assertDictContainsSubset({'action_set': True}, self.get_session())

    def test_attributes(self):
        self.login('gamma', 'gamma')
        in_({'user': 'gamma', 'id': 'gamma', 'role': 'user', 'password': 'gamma'},
            self.get_session()['user'])

    def test_logout_action(self):
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        in_({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])
        self.logout_ok(check_next='/dir/index/')
        self.assertTrue('user' not in self.get_session())

    def test_ensure_single_session(self):
        session1, session2 = requests.Session(), requests.Session()
        # log into first session
        self.session = session1
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        in_({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])
        # log into second session
        self.session = session2
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        in_({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])
        # first session should be logged out now
        self.session = session1
        self.assertTrue('user' not in self.get_session())

    def test_override(self):
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        in_({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])
        result = {'user': 'override', 'role': 'admin'}
        secret = gramex.service.app.settings['cookie_secret']
        cipher = create_signed_value(secret, 'user', json.dumps(result))
        session_data = self.get_session(headers={'X-Gramex-User': cipher})
        eq_(result, session_data['user'])

    def test_otp(self):
        self.session = requests.Session()
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        otp1 = self.session.get(server.base_url + '/auth/otp?expire=10').json()
        otp2 = self.session.get(server.base_url + '/auth/otp?expire=10').json()
        otp_dead = self.session.get(server.base_url + '/auth/otp?expire=0').json()
        in_({'user': 'alpha', 'id': 'alpha'}, self.get_session()['user'])

        self.session = requests.Session()
        self.assertTrue('user' not in self.get_session())
        session_data = self.get_session(headers={'X-Gramex-OTP': otp1})
        in_({'user': 'alpha', 'id': 'alpha'}, session_data['user'])

        self.session = requests.Session()
        self.assertTrue('user' not in self.get_session())
        session_data = self.session.get(server.base_url + '/auth/session',
                                        params={'gramex-otp': otp2}).json()
        in_({'user': 'alpha', 'id': 'alpha'}, session_data['user'])

        self.session = requests.Session()
        for otp in [otp1, otp2, otp_dead, 'nan']:
            r = self.session.get(server.base_url + '/auth/session', headers={'X-Gramex-OTP': otp})
            eq_(r.status_code, BAD_REQUEST)
            r = self.session.get(server.base_url + '/auth/session', params={'gramex-otp': otp})
            eq_(r.status_code, BAD_REQUEST)

    def test_apikey(self):
        # Get an API key as the user "alpha"
        self.session = requests.Session()
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')
        apikey = self.session.get(server.base_url + '/auth/apikey').json()

        def check_key(user, **kwargs):
            self.session = requests.Session()
            # Initially, a session does not have a logged in user
            self.assertTrue('user' not in self.get_session())
            # But when we call self.get_session() with the specified params / headers
            session_data = self.get_session(**kwargs)
            # it should return the user object we expect
            in_(user, session_data['user'])
            # ... and it should log the user in with that user object for that session
            in_(user, self.get_session()['user'])

        # A new session is not logged in by default, but setting ?gramex-key logs user in
        check_key({'user': 'alpha', 'id': 'alpha'}, params={'gramex-key': apikey})
        # A new session is not logged in by default, but setting X-Gramex-Key: header logs user in
        check_key({'user': 'alpha', 'id': 'alpha'}, headers={'X-Gramex-Key': apikey})

        # Get an API key as the user "new"
        self.session = requests.Session()
        apikey = self.session.get(server.base_url + '/auth/apikey?user=new&role=x').json()

        # A new session is not logged in by default, but setting ?gramex-key logs user in
        check_key({'user': 'new', 'role': 'x'}, params={'gramex-key': apikey})
        # A new session is not logged in by default, but setting X-Gramex-Key: header logs user in
        check_key({'user': 'new', 'role': 'x'}, headers={'X-Gramex-Key': apikey})

    def test_authorize(self):
        # If an Auth handler has an auth:, the auth: is ignored. Auth handlers are always open
        self.check('/auth/authorize')


class TestExpiry(AuthBase):
    # Just apply LoginMixin tests to AuthBase
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/expiry'

    def check_expiry(self, days):
        to_expire = time.time() + days * 24 * 60 * 60
        expires = {c.name: c.expires for c in self.session.cookies}.get('sid2', 0)
        self.assertLess(abs(to_expire - expires), 2)
        session = self.session.get(server.base_url + '/auth/session').json()
        self.assertLess(abs(to_expire - session.get('_t', 0)), 2)

    # Run additional tests for session and login features
    def test_expiry(self):
        self.login('alpha', 'alpha')
        self.check_expiry(gramex.conf.url['auth/expiry'].kwargs.session_expiry)


class TestInactive(AuthBase):
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/inactive'

    def test_inactive(self):
        self.login('alpha', 'alpha')
        # Get an initial session. Then visit quickly. After a second, get the last
        init_session = self.session.get(server.base_url + '/auth/session').json()
        visit_session = self.session.get(server.base_url + '/auth/session').json()
        session_expiry_delay = 1.1
        time.sleep(session_expiry_delay)
        last_session = self.session.get(server.base_url + '/auth/session').json()

        # init_session has the required keys
        inactive_days = gramex.conf.url['auth/inactive'].kwargs.session_inactive
        eq_(init_session['user']['user'], 'alpha')
        eq_(init_session['_i'], inactive_days * 24 * 60 * 60)
        self.assertIn('_l', init_session)

        # visit_session has not expired. But _l is updated
        self.assertGreater(visit_session['_l'], init_session['_l'])
        for key in ['_i', 'user', 'id']:
            eq_(init_session[key], visit_session[key])

        # last_session (after 1 second) has expired.
        for key in ['_i', '_l', 'user']:
            self.assertNotIn(key, last_session)
        self.assertNotEqual(init_session['id'], last_session['id'])


class TestCustomExpiry(TestExpiry):
    # Just apply LoginMixin tests to AuthBase
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/customexpiry'

    def test_custom_expiry(self):
        expiry_conf = gramex.conf.url['auth/customexpiry'].kwargs.session_expiry
        self.login('alpha', 'alpha')
        self.check_expiry(expiry_conf.default)
        self.login('alpha', 'alpha', post_args={'remember': 'day'})
        self.check_expiry(expiry_conf['values'].day)
        self.login('alpha', 'alpha', post_args={'remember': 'week'})
        self.check_expiry(expiry_conf['values'].week)
        self.login('alpha', 'alpha', post_args={'remember': 'na'})
        self.check_expiry(expiry_conf.default)


class TestAuthRedirect(AuthBase):
    # Just apply LoginMixin tests to AuthBase
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/simple-no-redirect'

    def test_redirect(self):
        next_url, ref_url = '/dir/index.html', '/dir/beta.html'
        # By default, if no redirect is specified, then ?next= is used
        self.login_ok('alpha', 'alpha', query_next=next_url, check_next=next_url)
        # If ?next= is missing, Referer is used
        self.login_ok('alpha', 'alpha', referer=ref_url, check_next=ref_url)
        # But ?next= takes precedence over Referer
        self.login_ok('alpha', 'alpha', query_next=next_url, referer=ref_url, check_next=next_url)
        # If neither is specified, use /
        self.login_ok('alpha', 'alpha', check_next='/')

    def test_post_redirect(self):
        # If we call the POST method WITHOUT calling the GET, it still redirects using
        # query: next and header: Referer
        self.check_direct_post_redirect(
            ({}, '/'),
            ({'headers': {'Referer': '/header'}}, '/header'),
            ({'data': {'next': '/query'}}, '/query'),
            ({'headers': {'Referer': '/header'}, 'data': {'next': '/query'}}, '/query'))


class TestAuthTemplate(TestGramex):
    def test_change_template(self):
        tempfiles.auth_template = auth_file = os.path.join(folder, 'authtemplate.html')
        shutil.copyfile(os.path.join(folder, 'auth.html'), auth_file)
        self.check('/auth/template', text='<h1>Auth</h1>')
        shutil.copyfile(os.path.join(folder, 'auth2.html'), auth_file)
        self.check('/auth/template', text='<h1>Auth 2</h1>')


class TestAuthPrepare(AuthBase):
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/prepare'

    def test_prepare(self):
        r = self.login('alpha', 'alpha1')
        eq_(r.status_code, UNAUTHORIZED)
        self.login_ok('alpha', 'alpha', check_next='/')
        self.login_ok('beta', 'beta', check_next='/')


class TestAuthActive(AuthBase):
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/active'

    def test_active_status(self):
        # Check that a non-logged-in-user has not record or no active status
        store = SQLiteStore(_user_info_path, table='user')

        # Log in. Then the user should have an active status
        self.login_ok('activeuser', 'activeuser1', check_next='/')
        activeuser_info = store.load('activeuser')
        eq_(activeuser_info['active'], 'y')

        # Log out. Then the user should not have an active status
        self.logout_ok(check_next='/dir/index/')
        activeuser_info = store.load('activeuser')
        eq_(activeuser_info['active'], '')


class TestUserKey(AuthBase):
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/userkey'

    def test_user_key(self):
        # /auth/userkey stores user info in session.userkey
        self.login_ok('alpha', 'alpha', check_next='/')
        session = self.session.get(server.base_url + '/auth/session').json()
        in_({'user': 'alpha', 'id': 'alpha'}, session.get('userkey'))
        eq_(session.get('user'), None)

        # This lets us have multiple logins
        self.url = server.base_url + '/auth/simple'
        self.login_ok('beta', 'beta', check_next='/dir/index/')
        session = self.session.get(server.base_url + '/auth/session').json()
        in_({'user': 'alpha', 'id': 'alpha'}, session.get('userkey'))
        in_({'user': 'beta', 'id': 'beta'}, session.get('user'))

        # ... and log out from just a single login
        self.session.get(server.base_url + '/auth/userkey_logout')
        session = self.session.get(server.base_url + '/auth/session').json()
        eq_(session.get('userkey'), None)
        in_({'user': 'beta', 'id': 'beta'}, session.get('user'))


class TestLookup(AuthBase):
    @classmethod
    def setUpClass(cls):
        AuthBase.setUpClass()
        cls.url = server.base_url + '/auth/lookup'

    def test_lookup(self):
        self.login_ok('alpha', 'alpha', check_next='/')
        session = self.session.get(server.base_url + '/auth/session').json()
        eq_(session['user']['gender'], 'male')

        self.login_ok('beta', 'beta', check_next='/')
        session = self.session.get(server.base_url + '/auth/session').json()
        eq_(session['user']['gender'], 'female')


class TestRules(AuthBase):
    url = server.base_url + '/auth/rulesdb'

    def test_default(self):
        self.login_ok('alpha', 'alpha', check_next='/')
        session = self.session.get(server.base_url + '/auth/session').json()
        eq_(session['user']['gender'], 'male')

        self.login_ok('beta', 'beta', check_next='/')
        session = self.session.get(server.base_url + '/auth/session').json()
        eq_(session['user']['gender'], 'female')
        eq_(session['user']['team'], 'Gramex')

        # When selector is a nonexistent attribute, nothing changes
        self.login_ok('γ', 'gamma', check_next='/')
        session = self.session.get(server.base_url + '/auth/session').json()
        eq_(session['user']['gender'], 'female')

        # Check if the empty string match for Gamma works
        eq_(session['user']['email'], 'gamma@null.com')

        upass = {'γ': 'gamma'}
        for user in 'alpha beta γ'.split():
            self.login_ok(user, upass.get(user, user), check_next='/')
            session = self.session.get(server.base_url + '/auth/session').json()
            # Check that no users have attributes defined in an unreachable rule
            neq_(session['user']['email'], 'none@none.com')
            # Check that everyone is team: Gramex
            eq_(session['user']['team'], 'Gramex')


class TestRulesFile(TestRules):
    url = server.base_url + '/auth/rulesfile'

    def test_default(self):
        super(TestRulesFile, self).test_default()
        upass = {'γ': 'gamma'}
        expires_duration = 3.14
        for user in 'alpha beta γ'.split():
            self.login_ok(user, upass.get(user, user), check_next='/')
            session = self.session.get(server.base_url + '/auth/session').json()
            eq_(session['user']['cookie_expires'], expires_duration)
            eq_(session['user']['expiry'], '2050-12-31T00:00:00+05:30')


class TestNoRules(AuthBase):
    url = server.base_url + '/auth/norules'

    def test_default(self):
        self.login_ok('alpha', 'alpha', check_next='/')
        session = self.session.get(server.base_url + '/auth/session').json()
        eq_(session['user']['gender'], 'female')

        self.login_ok('beta', 'beta', check_next='/')
        session = self.session.get(server.base_url + '/auth/session').json()
        eq_(session['user']['gender'], 'male')
        eq_(session['user']['team'], 'ग्रामेक्स')

        # When selector is a nonexistent attribute, nothing changes
        self.login_ok('γ', 'gamma', check_next='/')
        session = self.session.get(server.base_url + '/auth/session').json()
        eq_(session['user']['gender'], 'male')
        eq_(session['user']['empty'], '')


class DBAuthBase(AuthBase):
    @staticmethod
    def create_database(url, table):
        data = pd.read_csv(os.path.join(folder, 'userdata.csv'), encoding='cp1252')
        data['password'] = data['password'] + data['salt']
        dburl = sa.create_engine(url).url
        if dburl.drivername.startswith('postgresql'):
            dbutils.postgres_create_db(dburl.host, dburl.database, **{table: data})
        elif dburl.drivername.startswith('mysql'):
            dbutils.mysql_create_db(dburl.host, dburl.database, **{table: data})
        else:
            raise SkipTest('Unknown engine in ' + url)

    @classmethod
    def setUpClass(cls):
        super(DBAuthBase, cls).setUpClass()
        config = gramex.conf.url['auth/db'].kwargs
        cls.create_database(config.url, config.table)
        cls.url = server.base_url + '/auth/db'

    def test_empty(self):
        # issue: 399 DBAuth shouldn't accept empty username or password
        falsy = ['', None, 'abc']
        for (user, password) in [(x, y) for x in falsy for y in falsy]:
            r = self.login(user, password)
            # for valid but non-existent username, password
            if user and password:
                eq_(r.status_code, UNAUTHORIZED)
                self.assertIn('Cannot log in', r.text)
                continue
            eq_(r.status_code, BAD_REQUEST)
            self.assertIn('User name or password is empty', r.text)


class TestDBAuth(DBAuthBase, LoginMixin, LoginFailureMixin):
    # Just apply LoginMixin tests to DBAuthBase
    def test_salt(self):
        self.unauthorized('epsilon', 'epsilon')
        self.login_ok('epsilon', 'epsilon', headers={'salt': 'abc'}, check_next='/dir/index/')
        self.unauthorized('alpha', 'alpha', headers={'salt': 'abc'})
        self.login_ok('alpha', 'alpha', headers={'salt': '123'}, check_next='/dir/index/')


class TestDBCSVAuth(DBAuthBase, LoginMixin, LoginFailureMixin):
    @staticmethod
    def create_database(url):
        data = pd.read_csv(os.path.join(folder, 'userdata.csv'), encoding='cp1252')
        data['password'] = data['password'] + data['salt']
        data.to_csv(url, encoding='utf-8', index=False)
        tempfiles['dbcsv'] = url

    @classmethod
    def setUpClass(cls):
        super(DBAuthBase, cls).setUpClass()
        config = gramex.conf.url['auth/dbcsv'].kwargs
        cls.create_database(config.url)
        cls.url = server.base_url + '/auth/dbcsv'


class TestDBExcelAuth(DBAuthBase, LoginMixin, LoginFailureMixin):
    @staticmethod
    def create_database(url):
        writer = pd.ExcelWriter(url)
        dummy = pd.DataFrame({'x': [1, 2], 'y': [3, 4]})
        dummy.to_excel(writer, 'Sheet1', index=False)       # noqa - encoding not required
        data = pd.read_csv(os.path.join(folder, 'userdata.csv'), encoding='cp1252')
        data['password'] = data['password'] + data['salt']
        data.to_excel(writer, 'auth', index=False)          # noqa - encoding not required
        writer.save()
        tempfiles['dbexcel'] = url

    @classmethod
    def setUpClass(cls):
        super(DBAuthBase, cls).setUpClass()
        config = gramex.conf.url['auth/dbexcel'].kwargs
        cls.create_database(config.url)
        cls.url = server.base_url + '/auth/dbexcel'


class TestDBAuthSchema(DBAuthBase, LoginMixin):
    @classmethod
    def setUpClass(cls):
        super(DBAuthBase, cls).setUpClass()
        config = gramex.conf.url['auth/dbschema'].kwargs
        cls.create_database(config.url, config.table)
        cls.url = server.base_url + '/auth/dbschema'


class TestDBAuthSignup(DBAuthBase):
    @classmethod
    def setUpClass(cls):
        super(DBAuthBase, cls).setUpClass()
        cls.config = gramex.conf.url['auth/dbsignup'].kwargs
        cls.create_database(cls.config.url, cls.config.table)
        cls.url = server.base_url + '/auth/dbsignup'
        cls.LOGIN_TIMEOUT = 10

    def test_signup(self):
        # Visiting the page with ?signup shows the signup template
        session = requests.Session()
        r = session.get(self.url + '?signup')
        tree = self.check_css(r.text, ('h1', 'Signup'))

        # POST an empty username. Raises HTTP 400: User invalid
        r = session.post(self.url + '?signup', data={
            self.config.user.arg: '',
            self.config.forgot.get('arg', 'email'): 'any@example.org',
            '_xsrf': tree.xpath('.//input[@name="_xsrf"]')[0].get('value'),
        })
        eq_(r.status_code, BAD_REQUEST)
        self.assertIn('User cannot be empty', r.text)

        # POST an existing username. Raises HTTP 400: User exists
        r = session.post(self.url + '?signup', data={
            self.config.user.arg: 'alpha',
            self.config.forgot.get('arg', 'email'): 'any@example.org',
            '_xsrf': tree.xpath('.//input[@name="_xsrf"]')[0].get('value'),
        })
        eq_(r.status_code, BAD_REQUEST)
        self.assertIn('User exists', r.text)

        # POST a new username. That should send a email to our service
        r = session.post(self.url + '?signup', data={
            self.config.user.arg: 'newuser',
            self.config.forgot.get('arg', 'email'): 'any@example.org',
            '_xsrf': tree.xpath('.//input[@name="_xsrf"]')[0].get('value'),
        })
        eq_(r.status_code, OK)
        stubs = requests.get(server.base_url + '/email/stubs').json()
        ok_(len(stubs) > 0)
        mail = stubs[-1]
        self.assertDictContainsSubset({
            'host': gramex.conf.email.smtps_stub.host,
            'email': gramex.conf.email.smtps_stub.email,
            'password': gramex.conf.email.smtps_stub.password,
            'from_addr': gramex.conf.email.smtps_stub.email,
            'starttls': True,
            'to_addrs': ['any@example.org'],
            'quit': True,
        }, mail)
        obj = email.message_from_string(mail['msg'])
        msg = obj.get_payload(decode=True).decode('utf-8')
        ok_('auth/dbsignup?forgot=' in msg)
        token = msg.split('auth/dbsignup?forgot=')[1].split()[0]

        # Check that the user has been added to the users database
        user_engine = sa.create_engine(self.config.url)
        users = pd.read_sql(f'SELECT * FROM {self.config.table}', user_engine)
        users = users.set_index(self.config.user.column)
        user = users.loc['newuser']
        eq_(user['email'], 'any@example.org')

        # Check that the user has been added to the recovery database
        tokens = gramex.data.filter(**gramex.service.otp).set_index('token')
        eq_(tokens['user'][token], 'newuser')
        eq_(tokens['email'][token], 'any@example.org')

        # Log in with the URL sent in the email. That should take us to the
        # change password page. Change the password
        r = session.get(self.url + '?forgot=' + token)
        tree = lxml.html.fromstring(r.text)
        r = session.post(self.url + '?forgot=' + token, data={
            'password': 'newpassword',
            '_xsrf': tree.xpath('.//input[@name="_xsrf"]')[0].get('value'),
        })
        eq_(r.status_code, OK)
        users2 = pd.read_sql(f'SELECT * FROM {self.config.table}', user_engine)
        users2 = users2.set_index(self.config.user.column)
        user2 = users2.loc['newuser']
        ok_(user2[self.config.password.column] != user[self.config.password.column])

        # Check that we can log in
        self.login_ok('newuser', 'newpassword', check_next='/dir/index/')

        # TODO:
        # Allow a different key:
        # Allow different templates
        # Allow different columns to be added to the database
        # Check validation function return values


class TestAuthorize(DBAuthBase, LoginFailureMixin):
    def initialize(self, url, user='alpha', login_url='/login/', next_key='next'):
        self.session = requests.Session()
        r = self.session.get(server.base_url + url)
        eq_(r.url, server.base_url + login_url + '?' + urlencode({
            next_key: server.base_url + url}))
        r = self.session.post(server.base_url + url)
        eq_(r.url, server.base_url + url)
        eq_(r.status_code, UNAUTHORIZED)
        self.login_ok(user, user, check_next='/dir/index/')

    def test_auth_filehandler(self):
        self.initialize('/auth/filehandler')
        self.check('/auth/filehandler', path='dir/alpha.txt', session=self.session)

    def test_auth_functionhandler(self):
        self.initialize('/auth/functionhandler')
        self.check('/auth/functionhandler', text='OK', session=self.session)

    def test_auth_jsonhandler(self):
        self.initialize('/auth/jsonhandler/')
        r = self.check('/auth/jsonhandler/', session=self.session)
        eq_(r.json(), {'x': 1})

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
        url = '/auth/login-url'
        self.initialize(url, login_url='/auth/simple')
        # When requested as AJAX, no redirection happens
        xhr = {'X-Requested-With': 'XMLHttpRequest'}
        self.session = requests.Session()
        r = self.session.get(server.base_url + url, headers=xhr)
        eq_(r.status_code, UNAUTHORIZED)
        eq_(r.url, server.base_url + url)
        # But a successful AJAX auth DOES redirect
        self.login_ok('alpha', 'alpha', check_next='/dir/index/', headers=xhr)

        # X-Requested-With can be set to application-id by Android WebView
        # Redirect such requests to login URL
        xhr = {'X-Requested-With': 'Gramex.Android.WebView'}
        self.session = requests.Session()
        r = self.session.get(server.base_url + url, headers=xhr)
        eq_(r.status_code, OK)
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')

        # login_url: false does not redirect if no user
        url = '/auth/login-url-false'
        self.session = requests.Session()
        r = self.session.get(server.base_url + url)
        eq_(r.status_code, UNAUTHORIZED)
        eq_(r.url, server.base_url + url)
        self.login_ok('alpha', 'alpha', check_next='/dir/index/')

    def test_auth_custom_query(self):
        self.initialize('/auth/login-url-query', login_url='/auth/simple-query', next_key='later')

    def test_auth_template(self):
        self.initialize('/auth/unauthorized-template', user='alpha')
        self.check('/auth/unauthorized-template', code=FORBIDDEN,
                   text='403-template', session=self.session)
        self.initialize('/auth/unauthorized-template', user='beta')
        self.check('/auth/unauthorized-template', path='dir/alpha.txt', session=self.session)
