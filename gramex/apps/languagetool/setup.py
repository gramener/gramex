"""Download and install the LanguageTool app."""

import os
import tempfile
from zipfile import ZipFile

import requests
from tqdm import tqdm

from gramex.config import variables

fname = "LanguageTool-4.4.zip"
url = "https://languagetool.org/download/" + fname
ltdir = os.path.join(variables['GRAMEXDATA'], 'apps')


def install(chunksize=1024):
    cl = requests.head(url).headers.get('Content-Length', False)
    if cl:
        total = int(cl) // chunksize
    else:
        total = None

    resp = requests.get(url, stream=True)
    with tempfile.TemporaryFile() as tf:
        for chunk in tqdm(resp.iter_content(chunksize), total=total):
            tf.write(chunk)
        tf.seek(0)
        with ZipFile(tf) as zf:
            zf.extractall(ltdir)


if __name__ == '__main__':
    install()
