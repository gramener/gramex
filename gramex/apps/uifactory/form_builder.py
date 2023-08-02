import os
import gramex.data
from io import BytesIO
from ast import literal_eval
from PIL import Image
from gramex.config import variables as var, app_log
from gramex.handlers import Capture
from gramex.http import NOT_FOUND
from gramex.services import info
from gramex.transforms import handler
from tornado.web import HTTPError
import pandas as pd

FOLDER = os.path.abspath(os.path.dirname(__file__))
TARGET = os.path.join(var.GRAMEXDATA, 'uifactory', 'thumbnail')
capture = Capture(engine='chrome')

if not os.path.exists(TARGET):
    os.makedirs(TARGET)


def modify_columns(handler, data):
    if handler.request.method == 'GET' and len(data):
        # create dataframe from data, filter responses for the current form
        df = pd.DataFrame(data)
        df = df[df['form_id'].astype('int') == int(handler.get_argument('db'))]
        if df.shape[0] > 0:
            response = []
            for _, row in df.iterrows():
                response.append(literal_eval(row['response']))
            return pd.DataFrame(response)
        else:
            return pd.DataFrame.from_dict({"error": ["no entries yet"]})
    else:
        return data


def after_publish(handler, data):
    source_url = handler.xrequest_full_url.split('/publish')[0]
    if handler.request.method == 'POST':
        # Capture thumbnails for all missing entries.
        # This makes requests to this SAME server, while this function is running.
        # To avoid deadlock, run it in a thread.
        info.threadpool.submit(
            screenshots,
            handler.conf.kwargs,
            source_url,
            args={'thumbnail!': [], '_c': [var.FORMS_ID]},
        )
        return data
    elif handler.request.method == 'PUT':
        info.threadpool.submit(
            screenshots,
            handler.conf.kwargs,
            source_url,
            args={'_c': [var.FORMS_ID], 'id': [handler.get_argument('id')]},
        )
    elif handler.request.method == 'GET':
        return data
    elif handler.request.method == 'DELETE':
        _id = handler.get_argument('id')
        gramex.data.delete(url=var.FORMS_URL, table=var.FORMS_TABLE, args=handler.args, id=['id'])
        if os.path.exists(os.path.join(var.GRAMEXDATA, 'uifactory', f'form_{_id}.db')):
            os.remove(os.path.join(var.GRAMEXDATA, 'uifactory', f'form_{_id}.db'))


@handler
def endpoint(id: int, format: str, handler=None):
    row = gramex.data.filter(url=var.FORMS_URL, table=var.FORMS_TABLE, args={var.FORMS_ID: [id]})
    if len(row) == 0:
        raise HTTPError(NOT_FOUND)
    if format == 'json':
        # TODO: CORS
        handler.set_header('Content-Type', 'application/json')
        return row.config.iloc[0]
    elif format == 'html':
        # TODO: CORS
        return row.html.iloc[0]
    elif format == 'js':
        handler.set_header('Content-Type', 'application/javascript')
        return f'document.write(`{row.html.iloc[0]}`)'


def screenshots(kwargs, host, args):
    '''
    Loop through all entries that don't have a thumbnail and create it.
    '''
    try:
        # Get ID for all entries without a thumbnail
        pending = gramex.data.filter(url=var.FORMS_URL, table=var.FORMS_TABLE, args=args)
        width, height = 300, 300  # TODO: Change dimensions later
        for _index, row in pending.iterrows():
            id = row[var.FORMS_ID]
            url = f'{host}/form/{id}'
            # TODO: Use delay='renderComplete'
            content = capture.png(
                url, selector=".container", width=width, height=height, delay=1000
            )
            # Save under GRAMEXDATA/uifactory/thumbnail/<id>.png, cropped to width and height
            target = os.path.join(var.GRAMEXDATA, 'uifactory', 'thumbnail', f'{id}.png')
            Image.open(BytesIO(content)).crop((0, 0, width, height)).save(target)
            # Update the database with the thumbnail filename
            gramex.data.update(
                url=var.FORMS_URL,
                table=var.FORMS_TABLE,
                id=var.FORMS_ID,
                args={var.FORMS_ID: [id], 'thumbnail': [f'thumbnail/{id}.png']},
            )
    # Exceptions in a thread are not logged by default. Log them explicitly on console.
    # Otherwise, we won't know WHY something failed
    except Exception:
        app_log.exception('Screenshot failed')
        raise
