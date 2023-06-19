'''Handlers set up the micro-services for [gramex.services.url][].'''

from .basehandler import BaseMixin, BaseHandler, BaseWebSocketHandler, SetupFailedHandler
from .functionhandler import FunctionHandler
from .websockethandler import WebSocketHandler
from .filehandler import FileHandler
from .authhandler import AuthHandler, GoogleAuth, SimpleAuth, LogoutHandler
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
from .drivehandler import DriveHandler
from .comichandler import ComicHandler
from .openapihandler import OpenAPIHandler
from .messagehandler import MessageHandler
from .chatgpthandler import ChatGPTHandler

# Aliases
ChatGPT = ChatGPTHandler
Comic = ComicHandler
Command = ProcessHandler
Message = CommentHandler = MessageHandler
Data = FormHandler
Facebook = FacebookGraphHandler
File = DirectoryHandler = FileHandler
Filter = FilterHandler
Function = FunctionHandler
JSON = JSONHandler
OpenAPI = OpenAPIHandler
Proxy = ProxyHandler
Screenshot = CaptureHandler
Slide = PPTXHandler
Storage = DriveHandler
Twitter = TwitterRESTHandler
Upload = UploadHandler
Websocket = WebSocketHandler


__all__ = [
    'AuthHandler',
    'BaseHandler',
    'BaseWebSocketHandler',
    'BaseMixin',
    'Capture',
    'CaptureHandler',
    'ChatGPT',
    'ChatGPTHandler',
    'Command',
    'CommentHandler',
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
    'Message',
    'MessageHandler',
    'ModelHandler',
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


# MLHandler requires optional dependencies scikit-learn and statsmodels.
# If they're not installed, ignore the import error and skip MLHandler.
try:
    from .mlhandler import MLHandler, MLPredictor

    ML = MLHandler
    __all__ += ['ML', 'MLHandler', 'MLPredictor']
except ImportError as e:
    from gramex.config import app_log

    app_log.warning('url: MLHandler/MLPredictor dependency missing. %s', e)

try:
    # If Gramex enterprise is available, import all handlers
    import gramexenterprise.handlers

    if hasattr(gramexenterprise, 'handlers'):
        from gramexenterprise.handlers import *  # noqa

        __all__ += gramexenterprise.handlers.__all__
except ImportError:
    pass
