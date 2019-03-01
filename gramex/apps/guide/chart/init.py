import os
import gramex.cache

_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIGPATH = os.path.join(_DIR, 'config.yaml')
_ROOT = _DIR
_STOREDIR = os.path.join(_ROOT, '.store')

# data
IDESTOREDB = 'sqlite:///{}/app.builder.db'.format(_STOREDIR)
CONFIG = gramex.cache.open(_CONFIGPATH, 'config')
