import requests
from six.moves.http_client import OK
from . import server, TestGramex


class TestTwitterRESTHandler(TestGramex):
    'Test TwitterRESTHandler'

    def fetch(self, url, path, code=OK, **kwargs):
        r = requests.post(server.base_url + url + path, **kwargs)
        self.assertEqual(r.status_code, code, '%s: code %d != %d' % (url, r.status_code, code))
        return r

    def test_post(self):
        base = '/api/twitter/'
        self.fetch(base, 'search/tweets.json', 400)
        self.fetch(base, 'search/tweets.json?q=gramener&count=2')
        self.fetch(base, 'search/tweets.json', data={'q': 'gramener', 'count': 2})
        self.fetch(base, 'search/tweets.json', params={'q': 'gramener', 'count': 2})
        self.fetch(base, 'users/show.json', data={'screen_name': 'gramener'})
        self.fetch(base, 'statuses/user_timeline.json', params={'screen_name': 'gramener', 'count': 2})

    def test_get(self):
        r = requests.get(server.base_url + '/api/twitter/search/tweets.json?q=gramener&count=2')
        self.assertEqual(r.status_code, 405)
