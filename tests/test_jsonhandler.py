from __future__ import unicode_literals

import io
import os
import json
import requests
from gramex import conf
from orderedattrdict import AttrDict
from . import server
from .test_handlers import TestGramex

files = AttrDict()


def setUpModule():
    server.start_gramex()


def tearDownModule():
    server.stop_gramex()

    # Delete files created
    for filename in files.values():
        if os.path.exists(filename):
            os.unlink(filename)


def dump(data):
    return json.dumps(data, separators=(',', ':'))


class TestJSONHandler(TestGramex):
    'Test FileHandler'

    def test_get(self):
        data = conf.url['json/get'].kwargs.data
        self.check('/json/get/', text=dump(data))
        self.check('/json/get/x', text=dump(data.x))
        self.check('/json/get/x', text=dump(data.x))
        self.check('/json/get/y', text=dump(data.y))
        self.check('/json/get/z', text=dump(data.z))
        self.check('/json/get/z/0', text=dump(data.z[0]))
        self.check('/json/get/z/1', text=dump(data.z[1]))
        self.check('/json/get/z/2', text=dump(data.z[2]))
        self.check('/json/get/z/2/m', text=dump(data.z[2].m))
        self.check('/json/get/z/2/n', text=dump(data.z[2].n))

        self.check('/json/get//', text='null')
        self.check('/json/get/0', text='null')
        self.check('/json/get/na', text='null')
        self.check('/json/get/x/na', text='null')
        self.check('/json/get/z/3', text='null')
        self.check('/json/get/z/na', text='null')

    def put(self, url, **kwargs):
        return requests.put(server.base_url + url, timeout=1, **kwargs)

    def patch(self, url, **kwargs):
        return requests.patch(server.base_url + url, timeout=1, **kwargs)

    def delete(self, url, **kwargs):
        return requests.delete(server.base_url + url, timeout=1, **kwargs)

    def test_write(self):
        key, val = u'\u2013', -1
        key2, val2 = u'\u00A3', None
        data = {key: val}

        # put writes on root element, delete deletes it
        self.check('/json/write/', text='null')
        self.put('/json/write/', data=dump(data))
        self.check('/json/write/', text=dump(data))
        self.delete('/json/write/')

        # put creates deep trees
        self.check('/json/write/', text='null')
        self.put('/json/write/a/b', data=dump(data))
        self.check('/json/write/', text=dump({'a': {'b': data}}))
        self.delete('/json/write/')

        # trailing slash does not matter
        self.check('/json/write/', text='null')
        self.put('/json/write/a/b', data=dump(data))
        self.check('/json/write/', text=dump({'a': {'b': data}}))
        self.delete('/json/write/')

        # write into sub-keys
        self.check('/json/write/', text='null')
        self.put('/json/write/', data=dump(data))
        self.put(u'/json/write/%s/1' % key, data=dump(data))
        self.check('/json/write/', text=dump({key: {'1': data}}))
        self.delete('/json/write/')

        # test patch for update
        self.check('/json/write/', text='null')
        self.put('/json/write/', data=dump(data))
        self.patch('/json/write/', data=dump(data))
        self.check('/json/write/', text=dump(data))
        self.patch('/json/write/', data=dump({key: val2}))
        self.check('/json/write/', text=dump({key: val2}))
        self.patch('/json/write/', data=dump({key2: val}))
        self.check('/json/write/', text=dump({key: val2, key2: val}))
        self.delete('/json/write')


    def test_path(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        jsonfile = os.path.join(folder, 'jsonhandler.json')
        if os.path.exists(jsonfile):
            os.unlink(jsonfile)

        def match_jsonfile(data):
            self.check('/json/path/', text=dump(data))
            with io.open(jsonfile, encoding='utf-8') as handle:
                self.assertEqual(handle.read(), dump(data))

        self.check('/json/path/', text=dump(None))
        # At this point, jsonfile ought to be created, but the server thread may
        # not be done. So we'll test it later.

        key, val = u'\u2013', -1
        key2, val2 = u'\u00A3', None
        data = {key: val}

        # test put
        self.put('/json/path/', data=dump(data))
        match_jsonfile(data)

        # By this time, jsonfile definitely ought to be created -- since the
        # server thread has served the next request.
        self.assertTrue(os.path.exists(jsonfile))
        files.jsonfile = jsonfile

        # test put at a non-existent deep node
        self.put(u'/json/path/%s/1' % key, data=dump(data))
        match_jsonfile({key: {'1': data}})

        # test delete
        self.delete('/json/path/')
        match_jsonfile(None)

        # test patch
        self.put('/json/path/', data=dump(data))
        self.patch('/json/path/', data=dump(data))
        match_jsonfile(data)
        self.patch('/json/path/', data=dump({key: val2}))
        match_jsonfile({key: val2})
        self.patch('/json/path/', data=dump({key2: val}))
        match_jsonfile({key: val2, key2: val})

        # cleanup
        self.delete('/json/path')
