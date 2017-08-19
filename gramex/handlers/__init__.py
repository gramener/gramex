'''
Handlers
'''

from .basehandler import BaseHandler, BaseWebSocketHandler
from .functionhandler import FunctionHandler
from .websockethandler import WebSocketHandler
from .filehandler import FileHandler
from .datahandler import DataHandler, QueryHandler
from .authhandler import (GoogleAuth, FacebookAuth, TwitterAuth, LDAPAuth, SimpleAuth, DBAuth,
                          LogoutHandler)
from .processhandler import ProcessHandler
from .jsonhandler import JSONHandler
from .socialhandler import TwitterRESTHandler, FacebookGraphHandler
from .uploadhandler import UploadHandler
from .capturehandler import CaptureHandler, Capture

DirectoryHandler = FileHandler

__all__ = [
    'BaseHandler', 'FunctionHandler', 'FileHandler', 'DirectoryHandler',
    'DataHandler', 'QueryHandler', 'JSONHandler', 'GoogleAuth',
    'FacebookAuth', 'TwitterAuth', 'LDAPAuth', 'SimpleAuth', 'DBAuth',
    'LogoutHandler', 'ProcessHandler', 'TwitterRESTHandler',
    'FacebookGraphHandler', 'UploadHandler',
    'BaseWebSocketHandler', 'WebSocketHandler',
    'CaptureHandler', 'Capture',
]
