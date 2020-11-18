import os
import json
import time
import requests
import pandas as pd
import gramex.data
from shutil import rmtree
from mimetypes import guess_type
from tornado.web import create_signed_value
from gramex import conf
from gramex.http import (OK, BAD_REQUEST, NOT_FOUND, REQUEST_ENTITY_TOO_LARGE,
                         UNSUPPORTED_MEDIA_TYPE)
from gramex.install import _ensure_remove
from nose.tools import eq_, ok_
from pandas.util.testing import assert_frame_equal as afe
from . import server, TestGramex


class TestDriveHandler(TestGramex):
    @classmethod
    def setUpClass(cls):
        cls.kwargs = conf.url['drive'].kwargs
        cls.url = server.base_url + conf.url['drive'].pattern
        cls.dbpath = os.path.join(cls.kwargs.path, '.meta.db')
        cls.con = 'sqlite:///' + cls.dbpath

    def check_upload(self, *fileinfo, user={}, code=OK, check=True):
        files, data = [], {'tag': [], 'cat': []}
        for f in fileinfo:
            info = (f.get('name', f['file']), open(f['file'], 'rb'))
            if 'mime' in f:
                info += (f['mime'], )
            files.append(('file', info))
            for field in ('tag', 'cat'):
                if field in f:
                    data[field].append(f[field])
        headers = {}
        if user:
            secret = gramex.service.app.settings['cookie_secret']
            headers['X-Gramex-User'] = create_signed_value(secret, 'user', json.dumps(user))
        r = requests.post(self.url, files=files, data=data, headers=headers)
        eq_(r.status_code, code, '%s: code %d != %d' % (self.url, r.status_code, code))
        data = gramex.data.filter(self.con, table='drive')
        data = data.sort_values('id').tail(len(files))
        if not check:
            return
        for i, f in enumerate(fileinfo):
            result = data.iloc[i].to_dict()
            # If upload filehame has a path, only the basename is considered
            file = os.path.basename(f.get('name', f['file']))
            eq_(result['file'], file)
            # Extension is stored in lowercase even if filename is in uppercase
            eq_(result['ext'], os.path.splitext(f['file'])[1].lower())
            # Current time in seconds is stored as the date, to within a few seconds
            self.assertLess(time.time() - result['date'], 5)
            for field in ('tag', 'cat', 'user_id', 'user_role'):
                if field in f:
                    eq_(result[field], f[field])
                elif field[5:] in user:
                    eq_(result[field], user[field[5:]])
                else:
                    ok_(result[field] in {'', None})
            # File is stored in the target location
            os.path.exists(os.path.join(self.kwargs.path, f['file']))
        return data

    def row(self, id=-1):
        args = {'id': str(id)} if id >= 0 else {'_sort': 'id'}
        r = gramex.data.filter(self.con, table='drive', args=args)
        return r.irow[-1].to_dict() if len(r) else {}

    def test_upload(self):
        ok_(os.path.isfile(self.dbpath))
        data = gramex.data.filter(self.con, table='drive', args={})
        cols = ('id', 'file', 'ext', 'path', 'size', 'mime', 'user_id', 'user_role', 'tag', 'cat')
        for col in cols:
            ok_(col in data.columns, col)

        self.check_upload(dict(file='userdata.csv'))
        # If upload filehame has a path, only the basename is considered
        # Extension is stored in lowercase even if filename is in uppercase
        self.check_upload(dict(file='dir/image.JPG'))

        # If filename is repeated, it's extended randomly
        data = self.check_upload(dict(file='userdata.csv'))
        path = data.path.iloc[0]
        ok_(path != 'userdata.csv')
        ok_(path.startswith('userdata'))
        ok_(path.endswith('.csv'))

        # If filename has weird characters, it's hyphenated
        data = self.check_upload(dict(file='userdata.csv', name='β x.csv'))
        eq_(data.path.iloc[0], 'b-x.csv')

        # If content-type is available, it's used. Else it's guessed
        data = self.check_upload(dict(file='userdata.csv', mime='text/plain'))
        eq_(data.mime.iloc[0], 'text/plain')
        data = self.check_upload(dict(file='userdata.csv'))
        eq_(data.mime.iloc[0], guess_type('userdata.csv')[0])

        # Large files fail
        self.check_upload(dict(file='gramex.yaml'), code=REQUEST_ENTITY_TOO_LARGE, check=False)
        # .yaml disallowed because of allow
        self.check_upload(dict(file='gramextest.yaml'), code=UNSUPPORTED_MEDIA_TYPE, check=False)
        # .py disallowed because of exclude (though allow allows it)
        self.check_upload(dict(file='server.py'), code=UNSUPPORTED_MEDIA_TYPE, check=False)

        # Multi-uploads are supported, with tags
        self.check_upload(dict(file='userdata.csv', tag='t1'),
                          dict(file='actors.csv', tag='t2'))
        r = requests.post(self.url, files=(
            ('file', ('x.csv', open('userdata.csv', 'rb'))),
            ('file', ('y.csv', open('userdata.csv', 'rb'))),
        ), data={'tag': ['t1'], 'cat': ['c1', 'c2', 'c3'], 'rand': ['x', 'y']})
        eq_(r.status_code, OK)
        data = gramex.data.filter(self.con, table='drive').sort_values('id').tail(2)
        # If there are insufficient tags, they become empty strings
        eq_(data.tag.tolist(), ['t1', ''])
        # If there are more tags, they're truncated
        eq_(data.cat.tolist(), ['c1', 'c2'])
        # If there are irrelevant fields, they're ignored
        ok_('rand' not in data.columns)

        # ?id=..&_download downloads the file
        data = self.check_upload(dict(file='dir/index.html'))
        r = requests.get(self.url, params={'_download': '', 'id': data.id.iloc[0]})
        eq_(r.headers['Content-Disposition'], 'attachment; filename="index.html"')
        # TODO: FormHandler returns Content-Type using _format, so don't check for Content-Type
        # eq_(r.headers['Content-Type'], 'text/html')
        # Serves file with correct length despite unicode
        eq_(int(r.headers['Content-Length']), os.stat('dir/index.html').st_size)
        # If the ID is invalid, raises a NOT FOUND
        r = requests.get(self.url, params={'_download': '', 'id': 9999})
        eq_(r.status_code, NOT_FOUND)
        # If there are 2 IDs, it doesn't download
        r = requests.get(self.url, params={'_download': '', 'id': [0, 1]})
        eq_(r.headers['Content-Type'], 'application/json')

        # User attributes are captured on all files
        user = {'id': 'X', 'role': 'Y'}
        data = self.check_upload(dict(file='userdata.csv'), dict(file='actors.csv'), user=user)
        for index in range(2):
            eq_(data.user_id.iloc[index], 'X')
            eq_(data.user_role.iloc[index], 'Y')

        # DELETE ?id=... deletes the specified file
        data = gramex.data.filter(self.con, table='drive')
        indices = (0, 3, 6)
        for index in indices:
            r = requests.delete(self.url, params={'id': [data.id.iloc[index]]})
        data2 = gramex.data.filter(self.con, table='drive')
        eq_(len(data2), len(data) - len(indices))
        for index in indices:
            # Entry is removed from the database
            ok_(data.id.iloc[index] not in data2.id.values)
            # File is removed from the file system
            ok_(not os.path.exists(os.path.join(self.kwargs.path, data.path.iloc[index])))

        # DELETE without ?id= does not delete
        r = requests.delete(self.url)
        eq_(r.status_code, BAD_REQUEST)

        # PUT w/o file upload updates file, mime, ext, tags, etc.
        # NOT path, size, date, user_*
        data = gramex.data.filter(self.con, table='drive')
        params = {
            'id': data.id.iloc[0],
            'file': 'a.x',
            'ext': '.x',
            'mime': 'text/x',
            'tag': 't',
            'cat': 'c',
            'path': 'a.x',
            'size': 100,
            'date': 100,
            'user_id': 'A',
            'user_role': 'B'
        }
        r = requests.put(self.url, params=params)
        eq_(r.status_code, OK)
        data2 = gramex.data.filter(self.con, table='drive')
        new = data2[data2.id == data.id.iloc[0]].iloc[0]
        old = data[data.id == data.id.iloc[0]].iloc[0]
        for field in ('id', 'file', 'mime', 'ext', 'tag', 'cat'):
            eq_(new[field], params[field])
        for field in ('path', 'size', 'date', 'user_id', 'user_role'):
            eq_(new[field], old[field])
        # ... but with file upload updates size, date and user attributes
        params['id'] = data.id.iloc[1]
        files = (
            ('file', ('dir/text.txt', open('dir/text.txt', 'rb'))),
            # Even if multiple files are PUT, only the 1st is considered
            ('file', ('userdata', open('userdata.csv', 'rb'))),
        )
        secret = gramex.service.app.settings['cookie_secret']
        user = {'id': 'AB', 'role': 'CD'}
        r = requests.put(self.url, params=params, files=files, headers={
            'X-Gramex-User': create_signed_value(secret, 'user', json.dumps(user))
        })
        eq_(r.status_code, OK)
        data2 = gramex.data.filter(self.con, table='drive')
        new = data2[data2.id == data.id.iloc[1]].iloc[0]
        old = data[data.id == data.id.iloc[1]].iloc[0]
        for field in ('id', 'file', 'mime', 'ext', 'tag', 'cat'):
            eq_(new[field], params[field])
        eq_(new['path'], old['path'])
        eq_(new['size'], os.stat('dir/text.txt').st_size)
        ok_(time.time() - 2 <= new['date'] <= time.time())
        eq_(new['user_id'], user['id'])
        eq_(new['user_role'], user['role'])
        # Actual files are overwritten
        eq_(new['size'], os.stat(os.path.join(self.kwargs.path, new['path'])).st_size)

        # TEST: Nothing changes if ID is missing, even if file is present
        params['id'] = -1
        data = gramex.data.filter(self.con, table='drive')
        r = requests.put(self.url, params=params, files=files)
        data2 = gramex.data.filter(self.con, table='drive')
        afe(data, data2)

        # The modify: works even though we have a download override.
        # It sets the 'm' column to 'OK'
        data = pd.DataFrame(requests.get(self.url).json())
        ok_((data['m'] == 'OK').all())

        # TODO: When server is restarted, it has the new columns

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.kwargs.path):
            rmtree(cls.kwargs.path, onerror=_ensure_remove)
