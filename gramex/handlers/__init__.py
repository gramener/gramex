'''Handlers set up the micro-services for [gramex.services.url][].'''

from .basehandler import BaseMixin, BaseHandler, BaseWebSocketHandler, SetupFailedHandler
from .functionhandler import FunctionHandler
from .websockethandler import WebSocketHandler
from .filehandler import FileHandler
from .authhandler import GoogleAuth, SimpleAuth, LogoutHandler
from .processhandler import ProcessHandler
from .jsonhandler import JSONHandler
from .socialhandler import TwitterRESTHandler, FacebookGraphHandler
from .uploadhandler import UploadHandler
from .capturehandler import CaptureHandler, Capture
from .formhandler import FormHandler
from .pptxhandler import PPTXHandler
from .proxyhandler import ProxyHandler
from .modelhandler import ModelHandler
from .mlhandler import MLHandler, MLPredictor
from .filterhandler import FilterHandler
from .drivehandler import DriveHandler
from .comichandler import ComicHandler
from .openapihandler import OpenAPIHandler

# Aliases
Comic = ComicHandler
Command = ProcessHandler
Data = FormHandler
Facebook = FacebookGraphHandler
File = DirectoryHandler = FileHandler
Filter = FilterHandler
Function = FunctionHandler
JSON = JSONHandler
ML = MLHandler
OpenAPI = OpenAPIHandler
Proxy = ProxyHandler
Screenshot = CaptureHandler
Slide = PPTXHandler
Storage = DriveHandler
Twitter = TwitterRESTHandler
Upload = UploadHandler
Websocket = WebSocketHandler


__all__ = [
    'BaseHandler',
    'BaseWebSocketHandler',
    'BaseMixin',
    'Capture',
    'CaptureHandler',
    'Command',
    'Comic',
    'ComicHandler',
    'Data',
    'DirectoryHandler',
    'DriveHandler',
    'FacebookGraphHandler',
    'File',
    'FileHandler',
    'Filter',
    'FilterHandler',
    'FormHandler',
    'Function',
    'FunctionHandler',
    'GoogleAuth',
    'JSON',
    'JSONHandler',
    'LogoutHandler',
    'ModelHandler',
    'ML',
    'MLHandler',
    'MLPredictor',
    'OpenAPI',
    'OpenAPIHandler',
    'PPTXHandler',
    'ProcessHandler',
    'Proxy',
    'ProxyHandler',
    'Screenshot',
    'SetupFailedHandler',
    'SimpleAuth',
    'Slide',
    'Storage',
    'Twitter',
    'TwitterRESTHandler',
    'Upload',
    'UploadHandler',
    'Websocket',
    'WebSocketHandler',
]

try:
    # If Gramex enterprise is available, import all handlers
    import gramexenterprise.handlers

    if hasattr(gramexenterprise, 'handlers'):
        from gramexenterprise.handlers import *  # noqa

        __all__ += gramexenterprise.handlers.__all__
except ImportError:
    pass
