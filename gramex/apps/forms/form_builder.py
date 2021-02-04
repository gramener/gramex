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
TARGET = os.path.join(var.GRAMEXDATA, 'forms', 'thumbnail')
capture = Capture(engine='chrome')

if not os.path.exists(TARGET):
    os.makedirs(TARGET)


def modify_columns(handler, data):
    if handler.request.method == 'GET' and len(data):
        # process json response
        s = data['response'].apply(literal_eval)

        df_json = pd.concat([pd.DataFrame(x) for x in s], keys=s.index)
        df = pd.concat([data, df_json])
        df.reset_index()
        # collapse several rows (each row with all NaNs except one value) into one row
        return pd.concat([pd.Series(df[col].dropna().values, name=col) for col in df], axis=1)
    else:
        return data


def after_publish(handler, data):
    if handler.request.method == 'POST':
        # Capture thumbnails for all missing entries.
        # This makes requests to this SAME server, while this function is running.
        source_url = handler.xrequest_full_url.split('/publish')[0]
        # To avoid deadlock, run it in a thread.
        info.threadpool.submit(screenshots, handler.conf.kwargs, source_url)
        return data
    elif handler.request.method == 'GET':
        return data
    elif handler.request.method == 'DELETE':
        _id = handler.get_argument('id')
        gramex.data.delete(url=var.FORMS_URL, table=var.FORMS_TABLE, args=handler.args, id=['id'])
        os.remove(os.path.join(var.GRAMEXDATA, 'forms', f'form_{_id}.db'))


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


def screenshots(kwargs, host):
    '''
    Loop through all entries that don't have a thumbnail and create it.
    '''
    try:
        # Get ID for all entries without a thumbnail
        pending = gramex.data.filter(url=var.FORMS_URL, table=var.FORMS_TABLE,
                                     args={'thumbnail!': [], '_c': [var.FORMS_ID]})
        width, height = 300, 300    # TODO: Change dimensions later
        for index, row in pending.iterrows():
            id = row[var.FORMS_ID]
            url = f'{host}/form/{id}'
            # TODO: Use delay='renderComplete'
            content = capture.png(url, selector=".container", width=width, height=height,
                                  delay=1000)
            # Save under GRAMEXDATA/forms/thumbnail/<id>.png, cropped to width and height
            target = os.path.join(var.GRAMEXDATA, 'forms', 'thumbnail', f'{id}.png')
            Image.open(BytesIO(content)).crop((0, 0, width, height)).save(target)
            # Update the database with the thumbnail filename
            gramex.data.update(
                url=var.FORMS_URL, table=var.FORMS_TABLE, id=var.FORMS_ID,
                args={var.FORMS_ID: [id], 'thumbnail': [f'thumbnail/{id}.png']})
    # Exceptions in a thread are not logged by default. Log them explicitly on console.
    # Otherwise, we won't know WHY something failed
    except Exception:
        app_log.exception('Screenshot failed')
        raise
