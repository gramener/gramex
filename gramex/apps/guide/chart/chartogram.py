import os
import json
import io
import re
import time
import yaml
import sqlalchemy
import pandas as pd
import gramex.cache
import gramex.data
from binascii import hexlify
from orderedattrdict import AttrDict
from tornado.template import Template
from gramex.config import PathConfig, app_log, str_utf8, locate
from gramex.http import BAD_REQUEST
from init import IDESTOREDB, CONFIG, _DIR


def db_setup():
    engine = gramex.data.create_engine(IDESTOREDB, encoding=str_utf8)
    conn = engine.connect()
    conn.execute(CONFIG['SCHEMAS']['chart'])
    return IDESTOREDB


db_setup()

def randid():
    return hexlify(os.urandom(3)).decode('ascii')


def slugify(text, flag='-'):
    return re.sub(r'[\W_]+', flag, text.lower())


def unflatten(args):
    return {k: [v] for k, v in args.items()}


def charthandler(handler):
    '''
    Create a chart entry
    '''
    if handler.request.method == 'POST':
        appstate = _create_chart(handler)
        return appstate
    elif handler.request.method == 'GET':
        handler.kwargs.headers['Content-Type'] = 'text/html'
        row = gramex.data.filter(IDESTOREDB, table='chart', args={'id': handler.path_args})
        config = row['config'].values[0]

        return gramex.cache.open(os.path.join(_DIR, 'embed.template.html'), 'template').generate(myvalue = {
            'spec': config
        }).decode('utf-8')


def _create_chart(handler):
    hargs = AttrDict(json.loads(handler.request.body))
    chartname = slugify(hargs.chartname)
    user = (handler.current_user or {}).get('id', '-')
    args = {
        'id': randid(),
        'time': time.time(),
        'user': user,
        'config': json.dumps(hargs.spec),
        'name': hargs.chartname,
        'slug': chartname
    }
    gramex.data.insert(IDESTOREDB, table='chart', args=unflatten(args))
    appstate = {'chart': args}
    return json.dumps(appstate)
