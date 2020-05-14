import time
import unittest
import gramex.license
from nose.tools import eq_, ok_


class TestLicense(unittest.TestCase):
    def test_license(self):
        # On startup, license is already acccepted.
        # This is due to a 'gramex license accept' in .gitlab-ci.yml
        ok_(gramex.license.is_accepted())
        # Reject the license. It stays rejected
        gramex.license.reject()
        eq_(gramex.license.is_accepted(), False)
        # Accept the license. is_accepted() returns the current timestamp
        now = time.time()
        gramex.license.accept(force=True)
        ok_(abs(gramex.license.is_accepted() - now) < 1)
