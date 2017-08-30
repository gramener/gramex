import unittest
from orderedattrdict import AttrDict
from gramex.handlers.basehandler import check_membership


def check(auth, **kwargs):
    return


class TestMembership(unittest.TestCase):
    '''Test check_membership'''

    def check(self, condition, **kwargs):
        user = AttrDict(current_user=AttrDict(kwargs))
        self.assertEqual(all(self.auth(user)), condition)

    def test_no_condition(self):
        self.auth = check_membership([])
        # No conditions actually will NOT allow any user through.
        # If there are no conditions in gramex.yaml, we shouldn't be adding a check!
        self.check(False)

    def test_single_key(self):
        self.auth = check_membership([{'name': 'a'}])
        self.check(True, name='a')
        self.check(True, name=['x', 'a', 'y'])
        self.check(False, name='b')
        self.check(False)

    def test_nested_key(self):
        self.auth = check_membership([{'name.first': 'a'}])
        self.check(True, name={'first': 'a', 'last': 'b'})
        self.check(True, name={'first': ['x', 'a', 'y'], 'last': 'b'})
        self.check(False)
        self.check(False, name={})
        self.check(False, name={'first': ''})
        self.check(False, name={'first': 'b'})
        self.check(False, name={'last': 'a'})

    def test_multi_key(self):
        self.auth = check_membership([{'name': 'a', 'gender': 'm'}])
        self.check(True, name='a', gender='m')
        self.check(True, name=['x', 'a', 'y'], gender=['', 'x', 'm', 'f'])
        self.check(False, name='b', gender='m')
        self.check(False, name='b', gender=['m', ''])
        self.check(False, name='a', gender='f')
        self.check(False, name=['a', ''], gender='f')
        self.check(False, name='b', gender='f')
        self.check(False, name=[''], gender=[''])

    def test_multi_cond(self):
        self.auth = check_membership([{'name': 'a', 'gender': 'm'}, {'name': 'b', 'gender': 'f'}])
        self.check(True, name='a', gender='m')
        self.check(True, name=['a', 'b'], gender=['m', 'f'])
        self.check(True, name='b', gender='f')
        self.check(True, name=['a', 'x'], gender=['m', ''])
        self.check(True, name=['x', 'b'], gender='f')
        self.check(False)
        self.check(False, name='a', gender='f')
        self.check(False, name='b', gender='m')
        self.check(False, name='', gender='')
