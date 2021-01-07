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
        eq_(variables['SECRETS_DIR'], 'from_dir')
        eq_(variables['SECRETS_OVERRIDE_DIR'], 'from_root')
        eq_(variables['SECRETS_DICT'], 1)
        eq_(variables['SECRETS_DIR_A'], 1)
        eq_(variables['SECRETS_DIR_B'], 1)
