import requests
from six.moves.http_client import OK
from . import server, TestGramex


class TestTwitterRESTHandler(TestGramex):
    'Test TwitterRESTHandler'

    def fetch(self, url, path, code=OK, **kwargs):
        r = requests.post(server.base_url + url + path, **kwargs)
        self.assertEqual(r.status_code, code, '%s: code %d != %d' % (url, r.status_code, code))
        return r

    def test_get(self):
        self.fetch('/api/twitter/', 'search/tweets.json', 400)
        self.fetch('/api/twitter/', 'search/tweets.json?q=gramener&count=2', 200)
        self.fetch('/api/twitter/', 'search/tweets.json', 200, data={'q': 'gramener', 'count': 2})
        self.fetch('/api/twitter/', 'search/tweets.json', 200, params={'q': 'gramener', 'count': 2})
        self.fetch('/api/twitter/', 'users/show.json', 200, data={'screen_name': 'gramener'})
        self.fetch('/api/twitter/', 'statuses/user_timeline.json', 200, params={'screen_name': 'gramener', 'count': 2})
