import os
import unittest
from subprocess import run
from nose.tools import eq_


class TestSecrets(unittest.TestCase):
    def test_secrets(self):
        env = dict(os.environ)
        env.update(SECRET_A1='1', SECRET_A2='2', SECRET_B1='3', SECRET_B2='4')

        p = run(['secrets'], capture_output=True, env=env)
        eq_(p.stdout, b'')

        p = run(['secrets', 'SECRET_A1', 'SECRET_B2'], capture_output=True, env=env)
        eq_(p.stdout.splitlines(), [b"SECRET_A1: '1'", b"SECRET_B2: '4'"])

        p = run(['secrets', 'SECRET_A*', 'SECRET_B2', 'X=Y'], capture_output=True, env=env)
        eq_(p.stdout.splitlines(), [
            b"SECRET_A1: '1'",
            b"SECRET_A2: '2'",
            b"SECRET_B2: '4'",
            b"X: Y"])
