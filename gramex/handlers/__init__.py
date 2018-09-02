'''
Handlers
'''

from .basehandler import BaseHandler, BaseWebSocketHandler, SetupFailedHandler
from .functionhandler import FunctionHandler
from .websockethandler import WebSocketHandler
from .filehandler import FileHandler
from .datahandler import DataHandler, QueryHandler
from .authhandler import (GoogleAuth, FacebookAuth, TwitterAuth, LDAPAuth, SimpleAuth, DBAuth,
                          IntegratedAuth, LogoutHandler, SAMLAuth, OAuth2, SMSAuth, EmailAuth)
from .processhandler import ProcessHandler
from .jsonhandler import JSONHandler
from .socialhandler import TwitterRESTHandler, FacebookGraphHandler
from .uploadhandler import UploadHandler
from .capturehandler import CaptureHandler, Capture
from .formhandler import FormHandler
from .pptxhandler import PPTXHandler
from .proxyhandler import ProxyHandler
from .modelhandler import ModelHandler
from .filterhandler import FilterHandler

DirectoryHandler = FileHandler

__all__ = [
    'BaseHandler', 'FunctionHandler', 'FileHandler', 'DirectoryHandler',
    'DataHandler', 'QueryHandler', 'JSONHandler', 'GoogleAuth',
    'FacebookAuth', 'TwitterAuth', 'LDAPAuth', 'SimpleAuth', 'DBAuth', 'OAuth2',
    'IntegratedAuth', 'SAMLAuth', 'SMSAuth', 'EmailAuth',
    'LogoutHandler', 'ProcessHandler', 'TwitterRESTHandler',
    'FacebookGraphHandler', 'UploadHandler',
    'BaseWebSocketHandler', 'WebSocketHandler',
    'CaptureHandler', 'Capture',
    'FormHandler',
    'PPTXHandler',
    'ProxyHandler',
    'ModelHandler',
    'FilterHandler',
    'SetupFailedHandler',
]
