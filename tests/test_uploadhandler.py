# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import shutil
import requests
from gramex import conf
from gramex.install import _ensure_remove
from six.moves.http_client import OK, METHOD_NOT_ALLOWED
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

        self.assertTrue(os.path.isfile(os.path.join(self.path, '.meta.h5')))
        self.assertEqual(requests.get(server.base_url + url).status_code, METHOD_NOT_ALLOWED)
        tests = [
            {'files': {}},
            {'files': {'text': open('config.a.yaml')}, 'keys': ['config.a.yaml']},
            {'files': {'nopk': open('config.b.yaml')}},
            {'files': {'image': open('config.a.yaml')}, 'keys': ['config.a.1.yaml']},
            {'files': {'image': open('config.a.yaml'), 'text': open('config.b.yaml')},
             'keys': ['config.a.2.yaml', 'config.b.yaml']},
            {'files': {'unknown': ('file.csv', 'some,λ\nanother,λ\n')}, 'keys': ['file.csv']}]
        for test in tests:
            self.upload(url, **test)

        FileUpload(self.path).store.close()
        if os.path.exists(self.path):
            shutil.rmtree(self.path, onerror=_ensure_remove)
