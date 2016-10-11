from __future__ import unicode_literals
import requests
import lxml.html
from nose.plugins.skip import SkipTest
from gramex.http import OK, UNAUTHORIZED
from . import TestGramex
from . import server


class TestLDAPAuth(TestGramex):
    def login(self, user, password, url):
        r = requests.get(url)
        self.assertEqual(r.status_code, OK)
        tree = lxml.html.fromstring(r.text)

        # Create form submission data
        data = {'user': user, 'password': password}
        # TODO: set this as a cookie
        data['_xsrf'] = tree.xpath('.//input[@name="_xsrf"]')[0].get('value')

        # Submitting the correct password redirects
        return requests.post(url, timeout=10, data=data)

    def check(self, user, password, url, status_code, headers={}):
        self.url = server.base_url + url
        r = self.login(user, password, self.url)
        if r.status_code == UNAUTHORIZED and r.headers.get('Auth-Error', None) == 'conn':
            raise SkipTest('Unable to connect to LDAP server')
        self.assertEqual(r.status_code, status_code)
        # If the response is an OK response, go to home page. Else stay on login page
        if status_code == OK:
            self.assertEqual(r.url, server.base_url + '/')
        else:
            self.assertEqual(r.url, self.url)
        for key, value in headers.items():
            self.assertEqual(r.headers.get(key, None), value)

    def test_ldap(self):
        self.check('admin', 'Secret123', url='/auth/ldap', status_code=OK)

    def test_ldap_wrong_user(self):
        self.check('wrong-user', 'password', url='/auth/ldap', status_code=UNAUTHORIZED,
                   headers={'Auth-Error': 'auth'})

    def test_ldap_wrong_password(self):
        self.check('admin', 'wrong-password', url='/auth/ldap', status_code=UNAUTHORIZED,
                   headers={'Auth-Error': 'auth'})

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
