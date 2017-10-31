import unittest
from nose.tools import eq_
from gramex.apps.formhandler.formhandler_utils import URLUpdate, SET, ADD, POP, XOR


class TestURLUpdate(unittest.TestCase):
    def test_url(self):
        u = URLUpdate('')
        eq_(u(), '')                                                # Default test
        eq_(u(SET, 'x', '1'), 'x=1')                                # SET value
        eq_(u(SET, 'x', '1', SET, 'y', '2'), 'x=1&y=2')             # SET multiple values
        eq_(u(SET, 'x', '1', SET, 'x', None), '')                   # SET None clears
        eq_(u(ADD, 'x', '1'), 'x=1')                                # ADD new value
        eq_(u(SET, 'x', '1', ADD, 'x', '2'), 'x=1&x=2')             # ADD to existing value
        eq_(u(ADD, 'x', '1', ADD, 'x', '2'), 'x=1&x=2')             # ADD multiple values
        eq_(u(SET, 'x', '1', POP, 'x'), '')                         # POP None removes all values
        eq_(u(SET, 'x', '1', POP, 'x', None), '')                   # POP None removes all values
        eq_(u(SET, 'x', '1', POP, 'x', '1'), '')                    # POP removes value
        eq_(u(SET, 'x', '1', POP, 'x', '0'), 'x=1')                 # POP ignores missing vals
        eq_(u(XOR, 'x', '1'), 'x=1')                                # XOR sets missing
        eq_(u(SET, 'x', '1', XOR, 'x', '1'), '')                    # XOR clears existing

        u = URLUpdate('?x=1&x=2&y=3')
        eq_(u(), 'x=1&x=2&y=3')
        eq_(u(SET, 'x', '1'), 'x=1&y=3')                            # SET value
        eq_(u(SET, 'x', '1', SET, 'y', '2'), 'x=1&y=2')             # SET multiple values
        eq_(u(SET, 'x', '1', SET, 'x', None), 'y=3')                # SET None clears
        eq_(u(ADD, 'x', '1'), 'x=1&x=2&y=3')                        # ADD new value
        eq_(u(SET, 'x', '1', ADD, 'x', '2'), 'x=1&x=2&y=3')         # ADD to existing value
        eq_(u(ADD, 'x', '1', ADD, 'x', '2'), 'x=1&x=2&y=3')         # ADD multiple values
        eq_(u(SET, 'x', '1', POP, 'x', '1'), 'y=3')                 # POP removes value
        eq_(u(SET, 'x', '1', POP, 'x', '0'), 'x=1&y=3')             # POP ignores missing vals
        eq_(u(POP, 'x'), 'y=3')                                     # POP removes all values
        eq_(u(POP, 'x', None), 'y=3')                               # POP None removes all values
        eq_(u(POP, 'x', '1'), 'x=2&y=3')                            # POP removes part value
        eq_(u(POP, 'x', '2', POP, 'y', '3'), 'x=1')                 # POP multiple values
        eq_(u(POP, 'x', ADD, 'y', '4'), 'y=3&y=4')                  # POP in middle removes values
        eq_(u(POP, 'y', SET, 'x', '1'), 'x=1')                      # POP in middle removes values
        eq_(u(XOR, 'x', '1'), 'x=2&y=3')                            # XOR sets missing
        eq_(u(XOR, 'x', '2', XOR, 'y', '4'), 'x=1&y=3&y=4')         # XOR clears existing
