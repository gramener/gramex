from __future__ import unicode_literals

import io
import os
import json
import requests
from gramex import conf
from six.moves.http_client import OK
from . import server, tempfiles, TestGramex


def dump(data):
    return json.dumps(data, ensure_ascii=True)


class TestJSONHandler(TestGramex):
    'Test FileHandler'

    def json(self, method, url, compare='nocompare', code=OK, **kwargs):
        if 'data' in kwargs and isinstance(kwargs['data'], dict):
            kwargs['data'] = dump(kwargs['data'])
        r = getattr(requests, method)(server.base_url + url, timeout=1, **kwargs)
        self.assertEqual(r.status_code, code, '%s: code %d != %d' % (url, r.status_code, code))
        if compare != 'nocompare':
            self.assertEqual(json.loads(r.text), compare)
        return r

    def test_get(self):
        data = conf.url['json/get'].kwargs.data
        self.json('get', '/json/get/', data)
        self.json('get', '/json/get/x', data.x)
        self.json('get', '/json/get/x', data.x)
        self.json('get', '/json/get/y', data.y)
        self.json('get', '/json/get/z', data.z)
        self.json('get', '/json/get/z/0', data.z[0])
        self.json('get', '/json/get/z/1', data.z[1])
        self.json('get', '/json/get/z/2', data.z[2])
        self.json('get', '/json/get/z/2/m', data.z[2].m)
        self.json('get', '/json/get/z/2/n', data.z[2].n)

        self.json('get', '/json/get//', None)
        self.json('get', '/json/get/0', None)
        self.json('get', '/json/get/na', None)
        self.json('get', '/json/get/x/na', None)
        self.json('get', '/json/get/z/3', None)
        self.json('get', '/json/get/z/na', None)

    def test_write(self):
        key, val = u'\u2013', -1
        key2, val2 = u'\u00A3', None
        data = {key: val}

        # put writes on root element, delete deletes it
        self.json('get', '/json/write/', None)
        self.json('put', '/json/write/', data, data=data)
        self.json('get', '/json/write/', data)
        self.json('delete', '/json/write/', None)

        # Empty put does not raise an error, returns empty value
        r = self.json('put', '/json/write/', None, data='')

        # put creates deep trees
        self.json('get', '/json/write/', None)
        self.json('put', '/json/write/a/b', data, data=data)
        self.json('get', '/json/write/', {'a': {'b': data}})
        self.json('delete', '/json/write/', None)

        # write into sub-keys
        self.json('get', '/json/write/', None)
        self.json('put', '/json/write/', data, data=data)
        self.json('put', u'/json/write/%s/1' % key, data, data=data)
        self.json('get', '/json/write/', {key: {'1': data}})
        self.json('delete', '/json/write/', None)

        # test patch for update
        temp = {key: val}
        self.json('get', '/json/write/', None)
        self.json('put', '/json/write/', temp, data=temp)
        self.json('patch', '/json/write/', temp, data=temp)
        self.json('get', '/json/write/', temp)
        self.json('patch', '/json/write/', {key: val2}, data={key: val2})
        temp.update({key: val2})
        self.json('get', '/json/write/', temp)
        self.json('patch', '/json/write/', {key2: val}, data={key2: val})
        temp.update({key2: val})
        self.json('get', '/json/write/', temp)
        self.json('delete', '/json/write/', None)

        # test post for adding new keys
        self.json('get', '/json/write/', None)
        name = self.json('post', '/json/write/', data=data).json()['name']
        temp = {name: data}
        self.json('get', '/json/write/', temp)
        name = self.json('post', '/json/write/', data=data).json()['name']
        temp[name] = data
        self.json('get', '/json/write/', temp)
        self.json('delete', '/json/write/', None)

    def test_path(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        jsonfile = os.path.join(folder, 'jsonhandler.json')
        if os.path.exists(jsonfile):
            os.unlink(jsonfile)

        def match_jsonfile(compare):
            self.json('get', '/json/path/', compare)
            with io.open(jsonfile, encoding='utf-8') as handle:
                self.assertEqual(json.loads(handle.read()), compare)

        self.json('get', '/json/path/', None)
        # At this point, jsonfile ought to be created, but the server thread may
        # not be done. So we'll test it later.

        key, val = u'\u2013', -1
        key2, val2 = u'\u00A3', None
        data = {key: val}

        # test put
        self.json('put', '/json/path/', data, data=data)
        match_jsonfile(data)

        # By this time, jsonfile definitely ought to be created -- since the
        # server thread has served the next request.
        self.assertTrue(os.path.exists(jsonfile))
        tempfiles.jsonfile = jsonfile

        # test put at a non-existent deep node
        self.json('put', u'/json/path/%s/1' % key, data, data=data)
        match_jsonfile({key: {'1': data}})

        # test delete
        self.json('delete', '/json/path/', None)
        match_jsonfile(None)

        # test patch
        temp = {key: val}
        self.json('put', '/json/path/', temp, data=temp)
        self.json('patch', '/json/path/', temp, data=temp)
        match_jsonfile(temp)
        self.json('patch', '/json/path/', {key: val2}, data={key: val2})
        temp.update({key: val2})
        match_jsonfile(temp)
        self.json('patch', '/json/path/', {key2: val}, data={key2: val})
        temp.update({key2: val})
        match_jsonfile(temp)

        # cleanup
        self.json('delete', '/json/path/', None)
