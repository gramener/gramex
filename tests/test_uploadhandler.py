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
    @classmethod
    def setUpClass(cls):
        cls.path = conf.url['upload'].kwargs.path

    def upload(self, url, files, keys=[], data={}, code=OK):
        r = requests.post(server.base_url + url, files=files, data=data)
        self.assertEqual(r.status_code, code, '%s: code %d != %d' % (url, r.status_code, code))
        json = r.json()
        for key, rjs in zip(keys, json['upload']):
            self.assertTrue(os.path.isfile(os.path.join(self.path, key)))
            self.assertEqual(rjs['file'], key)
        if data:
            for val in json['delete']:
                self.assertEqual(val['key'], data['rm'])
                self.assertTrue(val['success'])
                self.assertFalse(os.path.isfile(os.path.join(self.path, data['rm'])))
        return r

    def test_upload(self):
        url = conf.url['upload'].pattern

        self.assertTrue(os.path.isfile(os.path.join(self.path, '.meta.h5')))
        self.assertEqual(requests.get(server.base_url + url).status_code, METHOD_NOT_ALLOWED)
        data = {'x': '1', 'y': 1}
        tests = [
            {'files': {}},
            {'files': {'text': open('userdata.csv')}, 'keys': ['userdata.csv'], 'data': data},
            {'files': {'nopk': open('actors.csv')}, 'data': data},
            {'files': {'image': open('userdata.csv')}, 'keys': ['userdata.1.csv'], 'data': data},
            {'files': {'image': open('userdata.csv'), 'text': open('actors.csv')},
             'keys': ['userdata.2.csv', 'actors.csv']},
            {'files': {'unknown': ('file.csv', 'some,λ\nanother,λ\n')}, 'keys': ['file.csv']},
            {'files': {'unknown': ('file', 'noextensionfile')}, 'keys': ['file']},
            {'files': {}, 'data': {'rm': 'file'}, 'data': data}]
        # requests fails for unicode filename :: RFC 7578 and nofilenames
        for test in tests:
            self.upload(url, **test)

    @classmethod
    def tearDownClass(cls):
        FileUpload(cls.path).store.close()
        if os.path.exists(cls.path):
            shutil.rmtree(cls.path, onerror=_ensure_remove)
