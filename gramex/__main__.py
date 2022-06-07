'''Gramex command line server.

Gramex can be run in 2 ways.

1. `python -m gramex` runs __main__.py.
2. `gramex` runs whatever is in `console_scripts` in `setup.py`

Both call `gramex.commandline()`.
'''

import gramex

gramex.commandline()
