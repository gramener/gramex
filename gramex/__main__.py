'''
Gramex command line server
'''

# There are 2 Gramex entry points: __main__.py and gramex.init().
# __main__.py is run by python -m gramex, gramex.exe, etc.
# gramex.init() is called after import gramex -- when using Gramex as a library.

import sys
import gramex

# Ask Gramex what command we're supposed to run, and just run it. This
# refactoring allows us to test gramex.commandline() to see if it processes the
# command line correctly, without actually running the commands.
callback, kwargs = gramex.commandline(sys.argv[1:])
callback(**kwargs)
