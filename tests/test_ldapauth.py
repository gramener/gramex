from __future__ import unicode_literals
import requests
import lxml.html
from nose.plugins.skip import SkipTest
from gramex.http import OK, UNAUTHORIZED
from . import TestGramex
from . import server


class TestLDAPAuth(TestGramex):
    session = requests.Session()

    def login(self, user, password, url):
        r = self.session.get(url)
        self.assertEqual(r.status_code, OK)
        tree = lxml.html.fromstring(r.text)

        # Create form submission data
        data = {'user': user, 'password': password}
        # TODO: set this as a cookie
        data['_xsrf'] = tree.xpath('.//input[@name="_xsrf"]')[0].get('value')

        # Submitting the correct password redirects
        return self.session.post(url, timeout=10, data=data)

    def check(self, user, password, url, status_code=None, headers={}, redirect='/'):
        self.url = server.base_url + url
        try:
            r = self.login(user, password, self.url)
        except requests.exceptions.ReadTimeout:
            raise SkipTest('Timeout connecting to LDAP server')
        if r.headers.get('Auth-Error', None) == 'conn':
            raise SkipTest('Unable to connect to LDAP server')
        if status_code is not None:
            self.assertEqual(r.status_code, status_code)
        # If the response is an OK response, go to home page. Else stay on login page
        if r.status_code == OK:
            self.assertEqual(r.url, server.base_url + redirect)
        else:
            self.assertEqual(r.url, self.url)
        for key, value in headers.items():
            self.assertEqual(r.headers.get(key, None), value)
        return r

    def test_ldap(self):
        r = self.check('manager', 'Secret123', url='/auth/ldap')
        # This runs tests on a public server.
        # If someone changes this server's credentials, this may fail until reset
        if r.status_code == UNAUTHORIZED:
            raise SkipTest('Password may have changed on LDAP server')
        else:
            self.assertEqual(r.status_code, OK)

    def test_ldap_wrong_user(self):
        self.check('wrong-user', 'password', url='/auth/ldap', status_code=UNAUTHORIZED,
                   headers={'Auth-Error': 'auth'})

    def test_ldap_wrong_password(self):
        self.check('admin', 'wrong-password', url='/auth/ldap', status_code=UNAUTHORIZED,
                   headers={'Auth-Error': 'auth'})

    def test_ldap_search(self):
        r = self.check('euler', 'password', url='/auth/ldap2-search', status_code=OK,
                       redirect='/auth/session')
        result = r.json()
        self.assertEqual(result['user']['attributes']['mail'], ['euler@ldap.forumsys.com'])
        self.assertIn('email:', result['user']['id'])
        self.assertIn('euler@ldap.forumsys.com', result['user']['id'])
        self.check('euler', 'wrong-password', url='/auth/ldap2-search', status_code=UNAUTHORIZED)

    def test_ldap_bind(self):
        self.check('gauss@ldap.forumsys.com', 'password', url='/auth/ldap2-bind',
                   status_code=OK)

    def test_ldap_bind_wrong_bind(self):
        self.check('anything', 'password', url='/auth/ldap2-bind-wrong-bind',
                   status_code=UNAUTHORIZED, headers={'Auth-Error': 'bind'})

    def test_ldap_bind_wrong_search(self):
        self.check('nonexistent@ldap.forumsys.com', 'password', url='/auth/ldap2-bind',
                   status_code=UNAUTHORIZED, headers={'Auth-Error': 'search'})

    def test_ldap_bind_wrong_password(self):
        self.check('gauss@ldap.forumsys.com', 'wrong-password', url='/auth/ldap2-bind',
                   status_code=UNAUTHORIZED, headers={'Auth-Error': 'auth'})
