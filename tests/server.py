import os
import time
import logging
import requests
import threading
from pathlib import Path
from orderedattrdict import AttrDict
import gramex

# Don't print the distracting DEBUG messages from some modules
for logger in ['matplotlib', 'MARKDOWN']:
    logging.getLogger(logger).setLevel(logging.WARNING)

info = AttrDict(
    folder=Path(__file__).absolute().parent,
    thread=None,
    exception=None,
)
base_url = 'http://localhost:9999'


def start_gramex():
    '''Run Gramex in this file's folder using the current gramex.conf.yaml'''
    # Don't start Gramex if it's already running
    if info.thread is not None:
        return

    def run_gramex():
        os.chdir(str(info.folder))
        try:
            gramex.init()
        except Exception as e:
            info.exception = e
        info.thread = None

    # Tornado 5.0 on Python 3 does not create an event loop on new threads.
    # See https://github.com/tornadoweb/tornado/issues/2183
    # Tell Tornado to explicitly create an event loop for our thread.
    try:
        import asyncio
        from tornado.platform.asyncio import AnyThreadEventLoopPolicy
        asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    except ImportError:
        pass

    info.thread = threading.Thread(name='server', target=run_gramex)
    info.thread.start()

    seconds_to_wait = 10
    attempts_per_second = 2
    for attempt in range(int(seconds_to_wait * attempts_per_second)):
        try:
            requests.get(base_url + '/', timeout=2.0)
            break
        # Catch any connection error, not timeout or or HTTP errors
        # http://stackoverflow.com/a/16511493/100904
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            logging.info('Could not connect to %s', base_url)
            if info.exception is None:
                time.sleep(1.0 / attempts_per_second)
            else:
                raise info.exception


def stop_gramex():
    '''Terminate Gramex'''
    requests.get(base_url + '/shutdown')
    tick = 0.1
    while info.thread:
        time.sleep(tick)
