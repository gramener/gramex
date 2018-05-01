import json
from copy import deepcopy
from orderedattrdict import AttrDict
import gramex


def crud(handler):
    method = handler.path_args[0]
    if method == 'post':
        conf = handler.get_argument('data', {})
        conf = json.loads(conf, object_pairs_hook=AttrDict)
        paths = deepcopy(gramex.paths)
        gramex.paths = AttrDict()
        gramex.init(new=conf)
        gramex.paths = paths
    elif method == 'init':
        gramex.init()
    # TODO: generated keys cannot be deleted from gramex.conf
    return gramex.conf
