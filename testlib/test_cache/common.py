'''
Used by testlib.test_cache.TestReloadModule.

This module features a single global array: val. When loaded, it is set to [0].
test_cache/mymodule.py is dynamically created and increments this variable. The
incremented value acts like a global counter, and we can test how often the
module is reloaded.
'''

val = [0]
