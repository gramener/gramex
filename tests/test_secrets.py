from . import TestGramex
from nose.tools import eq_


class TestSecrets(TestGramex):
    def test_secrets(self):
        # gramex.yaml is able to use variables in .secrets.yaml.
        self.check('/secrets', text='1 alpha 1 beta')
        # These variables are also in gramex.config.variables
        variables = self.check('/variables').json()
        eq_(variables['SECRET1'], 1)
        eq_(variables['SECRET2'], 'alpha')
        eq_(variables['REMOTE_SECRET1'], 1)
        eq_(variables['REMOTE_SECRET2'], 'beta')
