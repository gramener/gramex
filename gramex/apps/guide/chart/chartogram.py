import os
import json
import re
import time
import gramex.cache
import gramex.data
from binascii import hexlify
from gramex.config import str_utf8
from orderedattrdict import AttrDict
from gramex import variables


_DIR = os.path.dirname(os.path.abspath(__file__))


engine = gramex.data.create_engine(variables.CONFIGDB, encoding=str_utf8)
conn = engine.connect()

if engine.dialect.has_table(conn, "chart"):
    conn.execute(variables.SCHEMAS['chart'])


def randid():
    return hexlify(os.urandom(3)).decode('ascii')


def slugify(text, flag='-'):
    return re.sub(r'[\W_]+', flag, text.lower())


def unflatten(args):
    return {k: [v] for k, v in args.items()}


def _modify(handler):

    import pandas as pd
    return pd.DataFrame(handler.args)


def charthandler(handler):
    '''
    Create a chart entry
    '''
    if handler.request.method == 'POST':
        appstate = _create_chart(handler)
        return appstate
    elif handler.request.method == 'GET':
        handler.kwargs.headers['Content-Type'] = 'text/html'
        row = gramex.data.filter(variables.CONFIGDB, table='chart', args={'id': handler.path_args})

        return gramex.cache.open(os.path.join(_DIR, 'embed.template.html'), 'template').generate(
            myvalue={'spec': row['config'].values[0]}).decode('utf-8')


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
    gramex.data.insert(variables.CONFIGDB, table='chart', args=unflatten(args))
    appstate = {'chart': args}
    return json.dumps(appstate)
