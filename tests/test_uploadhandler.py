import os
import shutil
import requests
from gramex import conf
from gramex.install import _ensure_remove
from six.moves.http_client import OK
from gramex.handlers.uploadhandler import FileUpload
from . import server, TestGramex


class TestUploadHandler(TestGramex):
    'Test UploadHandler'

    def upload(self, url, files, keys=[], code=OK):
        r = requests.post(server.base_url + url, files=files)
        self.assertEqual(r.status_code, code, '%s: code %d != %d' % (url, r.status_code, code))
        json = r.json()
        for key, rjs in zip(keys, json):
            self.assertTrue(os.path.isfile(os.path.join(self.path, key)))
            self.assertEqual(rjs['file'], key)
        return r

    def test_upload(self):
        self.path = conf.url['upload'].kwargs.path
        url = conf.url['upload'].pattern
        assert os.path.isfile(os.path.join(self.path, '.meta.h5'))
        self.upload(url, {})
        self.upload(url, {'text': open('config.a.yaml')}, ['config.a.yaml'])
        self.upload(url, {'nopk': open('config.b.yaml')})
        self.upload(url, {'image': open('config.a.yaml')}, ['config.a.1.yaml'])
        self.upload(url, {'image': open('config.a.yaml'), 'text': open('config.b.yaml')},
                    ['config.a.2.yaml', 'config.b.yaml'])

        FileUpload(self.path).store.close()
        if os.path.exists(self.path):
            shutil.rmtree(self.path, onerror=_ensure_remove)
