'''
Gramex command line server
'''

# There are 2 Gramex entry points: __main__.py and gramex.commandline().
# __main__.py is run by python -m gramex.
# gramex.commandline() is run by gramex.exe.
# gramex.init() is called after import gramex -- when using Gramex as a library.

import gramex

gramex.commandline()
