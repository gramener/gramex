import os
import sys
import time
import uuid
import gramex
from gramex.config import variables
from gramex.cache import SQLiteStore


# gramex.license.EULA has the wording of the end user license agreement
EULA = '''
-------------------------------------------------------------------------
Read the license agreement at https://gramener.com/gramex/guide/license/
'''
# All license information is captured in this store.
store = SQLiteStore(path=os.path.join(variables['GRAMEXDATA'], 'license.db'), table='license')


def is_accepted():
    '''
    If license was accepted, returns timestamp when license was accepted.
    If license was never accepted so far, returns None.
    If license was rejected, returns False.
    '''
    return store.load('accepted', default=None)


def accept(force=False):
    '''
    Prints the license.
    Allows users to accept the license by prompting.
    If force=True is passed, accepts the license with no prompt.
    If no stdin is available, e.g. when running as a service, accept license with no prompt.
    '''
    if is_accepted():
        return
    gramex.console(EULA)
    result = 'y' if force or not sys.stdin else ''
    while not result:
        result = input('Do you accept the license (Y/N): ').strip()
    if result.lower().startswith('y'):
        store.dump('accepted', time.time())
        store.flush()
        gramex.console('Gramex license accepted')
    else:
        raise RuntimeError('Gramex license not accepted')


def reject():
    '''
    Rejects the license.
    '''
    store.dump('accepted', False)
    store.flush()
    gramex.console('Gramex license rejected')


'''
This section may implement different strategies to uniquely identify machines.

http://serialsense.com/blog/2011/02/generating-unique-machine-ids/
http://stackoverflow.com/questions/2461141/get-a-unique-computer-id-in-python-on-windows-and-linux
'''


def mac_id():
    return uuid.getnode()


def cpu_id():
    raise NotImplementedError('CPU ID not yet implemented')


def bios_id():
    raise NotImplementedError('BIOS ID not yet implemented')
