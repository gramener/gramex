import os
import json
from io import open
from glob import glob
from orderedattrdict import AttrDict
from tornado.template import Template


folder = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(folder, '../../gramex/release.json'), encoding='utf-8') as handle:
    release = json.load(handle, object_pairs_hook=AttrDict)

for path in glob(os.path.join(folder, '*.tmpl')):
    with open(path, encoding='utf-8') as handle:
        content = Template(handle.read()).generate(release=release)
    with open(path.replace('.tmpl', '.sh'), 'wb') as handle:
        handle.write(content)
