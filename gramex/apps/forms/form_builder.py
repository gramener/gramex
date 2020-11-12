import os
import re
import sqlite3
import gramex.data
from io import BytesIO
from PIL import Image
from gramex.config import variables as var, app_log
from gramex.handlers import Capture
from gramex.http import NOT_FOUND
from gramex.services import info
from gramex.transforms import handler
from tornado.web import HTTPError

FOLDER = os.path.abspath(os.path.dirname(__file__))
TARGET = os.path.join(var.GRAMEXDATA, 'forms', 'thumbnail')
capture = Capture(engine='chrome')

if not os.path.exists(TARGET):
    os.makedirs(TARGET)


def after_publish(handler, data):
    if handler.request.method == 'POST':
        # Capture thumbnails for all missing entries.
        # This makes requests to this SAME server, while this function is running.
        # To avoid deadlock, run it in a thread.
        info.threadpool.submit(screenshots, handler.conf.kwargs)
        # fetch id of the last inserted form by the user
        rows = gramex.data.filter(url=var.FORMS_URL, table=var.FORMS_TABLE, args={
            'user': [handler.current_user.id]})
        return {'id': rows['id'].max()}
    else:
        return data


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


def screenshots(kwargs):
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
            url = f'http://localhost:9988/form/{id}'   # TODO: Dynamically find port & URL
            # TODO: Use delay='renderComplete'
            content = capture.png(url, selector='#view-form', width=width, delay=1000)
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


def db_check(handler):
    """Create forms.db if it doesn't exist."""
    db_path = var['FORMS_URL']
    db_path = re.sub(r'^sqlite:///', '', db_path)
    if(not os.path.isfile(db_path)):
        conn = sqlite3.connect(db_path)
        conn.execute('CREATE TABLE "new_table" (`id` INTEGER PRIMARY KEY AUTOINCREMENT,\
            `metadata` TEXT, `config` TEXT, `thumbnail` TEXT, `html` TEXT, `user` TEXT)')
        conn.close()
        return "created database"
    else:
        return "db exists"
