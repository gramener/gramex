'''
Used by testlib.test_cache.TestReloadModule.

Every time this module is reloaded, it increments common.va[0] by one.
'''

import common

common.val[0] += 1
