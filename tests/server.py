import os
import sys
import time
import logging
import requests
import subprocess
from pathlib import Path
from orderedattrdict import AttrDict

info = AttrDict(
    folder=Path(__file__).absolute().parent,
    process=None,
)
base_url = 'http://localhost:9999'


def start_gramex():
    "Run Gramex in this file's folder using the current gramex.conf.yaml"
    # Don't start Gramex if it's already running
    if info.process is not None:
        return

    # Ensure that PYTHONPATH has this repo and ONLY this repo
    env = dict(os.environ)
    env['PYTHONPATH'] = str(info.folder.parent)
    info.process = subprocess.Popen(
        [sys.executable, '-m', 'gramex'],
        cwd=str(info.folder),
        env=env,
        # stdout=getattr(subprocess, 'DEVNULL', open(os.devnull, 'w')),
    )

    # Wait until Gramex has started
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
    info.process.terminate()
    info.process = None
