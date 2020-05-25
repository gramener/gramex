import os
import re
import six
import shutil
import requests
import gramex.cache
from datetime import datetime
from nose.tools import eq_, ok_
from gramex import conf
from gramex.install import _ensure_remove
from gramex.http import OK, METHOD_NOT_ALLOWED, FORBIDDEN
from gramex.handlers.uploadhandler import FileUpload
from . import server, TestGramex


class TestUploadHandler(TestGramex):
    response_keys = ['key', 'filename', 'file', 'created', 'user', 'size', 'mime', 'data']

    @classmethod
    def setUpClass(cls):
        cls.path = six.text_type(conf.url['upload'].kwargs.path)
        cls.info = FileUpload(cls.path)

    def check_upload(self, url, files, names=[], data={}, code=OK):
        r = requests.post(url, files=files, data=data)
        eq_(r.status_code, code, '%s: code %d != %d' % (url, r.status_code, code))
        json = r.json()
        meta = self.info.info()
        for index, name in enumerate(names):
            upload = json['upload'][index]
            ok_(os.path.isfile(os.path.join(self.path, name)))
            eq_(upload['file'], name)
            ok_(upload['file'] in meta)
            meta_entry = meta[upload['file']]
            for key in self.response_keys:
                self.assertIn(key, upload)
                # TODO: check that upload[key] has the correct value
                eq_(meta_entry[key], upload[key])
        if data:
            for val in json['delete']:
                eq_(val['key'], data['rm'])
                ok_(val['success'])
                self.assertFalse(os.path.isfile(os.path.join(self.path, data['rm'])))
        return r

    def test_upload(self):
        url = server.base_url + conf.url['upload'].pattern
        ok_(os.path.isfile(os.path.join(self.path, '.meta.db')))
        eq_(requests.get(url).status_code, METHOD_NOT_ALLOWED)
        data = {'x': '1', 'y': 1}
        up = lambda **kwargs: self.check_upload(url, **kwargs)      # noqa
        # Empty upload
        up(files={})
        # Single upload with data
        up(files={'text': open('userdata.csv', 'rb')}, names=['userdata.csv'], data=data)
        # Single upload with data but with wrong key - gets ignored
        up(files={'nokey': open('actors.csv', 'rb')}, names=[], data=data)
        # Second upload creates a copy of the file with a new filename
        up(files={'text': open('userdata.csv', 'rb')}, names=['userdata.1.csv'], data=data)
        # Multiple uploads
        up(files={'image': open('userdata.csv', 'rb'), 'text': open('actors.csv', 'rb')},
           names=['userdata.2.csv', 'actors.csv'])
        # Filename with no extension, hence no MIME type
        up(files={'unknown': ('file', open('actors.csv', 'rb'))}, names=['file'])
        # Save uploaded file as specific filename
        up(files={'text': open('actors.csv', 'rb')}, names=['α'], data={'save': 'α'})
        # Save file under a sub-directory
        up(files={'text': open('actors.csv', 'rb')}, names=['高/α'], data={'save': '高/α'})
        # Multiple uploads with renames
        up(files={'image': open('userdata.csv', 'rb'), 'text': open('actors.csv', 'rb')},
           names=['β', 'γ'], data={'save': ['β', 'γ']})
        # Delete file
        up(files={}, data={'rm': 'file'})

        # Outside paths fail
        for path in ['../actors.csv', '/actors.csv', '../upload/../β']:
            r = requests.post(url, files={'text': open('actors.csv', 'rb')}, data={'save': path})
            eq_(r.status_code, FORBIDDEN)
            msg = r.reason.decode('utf-8') if isinstance(r.reason, six.binary_type) else r.reason
            ok_('outside' in msg)

    def test_upload_error(self):
        url = server.base_url + conf.url['upload-error'].pattern
        for path in ['δ', 'ε']:
            r = requests.post(url, files={'file': open('actors.csv', 'rb')}, data={'save': path})
            eq_(r.status_code, OK)
            r = requests.post(url, files={'file': open('actors.csv', 'rb')}, data={'save': path})
            eq_(r.status_code, FORBIDDEN)
            r = requests.post(url, files={'file': open('actors.csv', 'rb')}, data={'save': path})
            eq_(r.status_code, FORBIDDEN)
            msg = r.reason.decode('utf-8') if isinstance(r.reason, six.binary_type) else r.reason
            ok_('file exists' in msg)

    def test_upload_overwrite(self):
        url = server.base_url + conf.url['upload-overwrite'].pattern
        base = conf.url['upload-overwrite'].kwargs.path
        read = lambda f: gramex.cache.open(f, 'text', rel=True)     # noqa
        for path in ['ζ', 'η']:
            r = requests.post(url, files={'file': open('actors.csv', 'rb')}, data={'save': path})
            eq_(r.status_code, OK)
            eq_(read(os.path.join(base, path)), read('actors.csv'))
            r = requests.post(url, files={'file': open('userdata.csv', 'rb')}, data={'save': path})
            eq_(r.status_code, OK)
            eq_(read(os.path.join(base, path)), read('userdata.csv'))

    def test_upload_backup(self):
        url = server.base_url + conf.url['upload-backup'].pattern
        base = conf.url['upload-backup'].kwargs.path
        read = lambda f: gramex.cache.open(f, 'text', rel=True)     # noqa
        for path in ['θ', 'λ']:
            r = requests.post(url, files={'file': open('actors.csv', 'rb')}, data={'save': path})
            eq_(r.status_code, OK)
            eq_(read(os.path.join(base, path)), read('actors.csv'))
            # Ensure that a backup file is created, and has the correct contents
            r = requests.post(url, files={'file': open('userdata.csv', 'rb')}, data={'save': path})
            eq_(r.status_code, OK)
            eq_(read(os.path.join(base, path)), read('userdata.csv'))
            backup = r.json()['upload'][0].get('backup', None)
            name, ext = os.path.splitext(path)
            backup_re = r'{}.{:%Y%m%d-%H}\d\d\d\d{}'.format(name, datetime.now(), ext)
            ok_(re.match(backup_re, backup))
            eq_(read(os.path.join(base, backup)), read('actors.csv'))

    def test_upload_transform(self):
        for path in ['upload-transform', 'upload-transform-blank']:
            url = server.base_url + conf.url[path].pattern
            r = requests.post(url, files={'file': open('actors.csv', 'rb')}, data={'data': 1})
            eq_(r.status_code, OK)
            upload = r.json()['upload'][0]
            meta_entry = self.info.info()[upload['file']]
            eq_(upload, meta_entry)

    @classmethod
    def tearDownClass(cls):
        FileUpload(cls.path).store.close()
        if os.path.exists(cls.path):
            try:
                shutil.rmtree(cls.path, onerror=_ensure_remove)
            except OSError:
                # .meta.db may be in use. Ignore it.
                pass
