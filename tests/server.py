import os
import time
import logging
import requests
import threading
from pathlib import Path
from orderedattrdict import AttrDict
import gramex

info = AttrDict(
    folder=Path(__file__).absolute().parent,
    thread=None,
)
base_url = 'http://localhost:9999'


def start_gramex():
    "Run Gramex in this file's folder using the current gramex.conf.yaml"
    # Don't start Gramex if it's already running
    if info.thread is not None:
        return

    def run_gramex():
        os.chdir(str(info.folder))
        gramex.init()

    info.thread = threading.Thread(name='server', target=run_gramex)
    info.thread.start()

    seconds_to_wait = 10
    attempts_per_second = 2
    for attempt in range(int(seconds_to_wait * attempts_per_second)):
        try:
            requests.get(base_url + '/')
            break
        # Catch any connection error, not timeout or or HTTP errors
        # http://stackoverflow.com/a/16511493/100904
        except requests.exceptions.ConnectionError:
            logging.info('Could not connect to %s', base_url)
            time.sleep(1.0 / attempts_per_second)


def stop_gramex():
    'Terminate Gramex'
    if info.thread is not None:
        gramex.shutdown()
        info.thread = None
