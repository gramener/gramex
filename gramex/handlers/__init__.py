'''
Handlers
'''

from .functionhandler import FunctionHandler
from .filehandler import FileHandler
from .datahandler import DataHandler
from .authhandler import (GoogleAuth, FacebookAuth, TwitterAuth, LDAPAuth)
from .processhandler import ProcessHandler
from .jsonhandler import JSONHandler


DirectoryHandler = FileHandler

__all__ = ['FunctionHandler', 'FileHandler', 'DirectoryHandler', 'DataHandler', 'JSONHandler',
           'GoogleAuth', 'FacebookAuth', 'TwitterAuth', 'LDAPAuth', 'ProcessHandler']
