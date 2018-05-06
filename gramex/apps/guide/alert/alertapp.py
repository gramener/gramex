import json
import yaml
from tornado.web import HTTPError
from tornado.gen import coroutine, Return
from gramex.http import INTERNAL_SERVER_ERROR
from gramex.services import create_alert, info
from orderedattrdict.yamlutils import AttrDictYAMLLoader


@coroutine
def sendmail(handler):
    # Create a key: value configuration from the arguments
    conf = yaml.load(handler.get_arg('conf'), Loader=AttrDictYAMLLoader)    # nosec
    if not isinstance(conf, dict):
        raise HTTPError(INTERNAL_SERVER_ERROR, reason='Config should be a dict')
    conf.setdefault('service', 'alert-gmail')
    alert = create_alert('guide-alert', conf)
    if alert is None:
        raise HTTPError(INTERNAL_SERVER_ERROR, reason='Cannot create alert with this config')
    kwargs = yield info.threadpool.submit(alert)
    if kwargs is None:
        raise HTTPError(INTERNAL_SERVER_ERROR, reason='Could not run this config')
    raise Return(json.dumps(kwargs, indent=2))
