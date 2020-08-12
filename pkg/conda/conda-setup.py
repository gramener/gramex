import os
import json
from io import open
from glob import glob
from orderedattrdict import AttrDict
from shutil import copy
from tornado.template import Template


folder = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(folder, '../../gramex/release.json'), encoding='utf-8') as handle:
    release = json.load(handle, object_pairs_hook=AttrDict)

for path in glob(os.path.join(folder, 'template.*')):
    with open(path, encoding='utf-8') as handle:
        content = Template(handle.read()).generate(release=release, json=json)
    with open(path.replace('template.', ''), 'wb') as handle:
        handle.write(content)

# Copy license file
copy(os.path.join(folder, '../../LICENSE'), os.path.join(folder, 'LICENSE'))
