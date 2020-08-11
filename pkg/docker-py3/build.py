import os
from docker import from_env
from tornado.template import Template
import json
from orderedattrdict import AttrDict


client = from_env()
folder = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(folder, '../../gramex/release.json'), encoding='utf-8') as handle:
    release = json.load(handle, object_pairs_hook=AttrDict)

with open(os.path.join(folder, 'Dockerfile.tmpl'), encoding='utf8') as fin:
    content = Template(fin.read()).generate(version=release.version)

with open(os.path.join(folder, 'Dockerfile'), 'wb') as fout:
    fout.write(content)

_, log = client.images.build(path=folder, tag=f'gramener/gramex:{release.version}', rm=True)
for msg in log:
    for k, v in msg.items():
        print(k, "\t", v)
