import requests
import concurrent.futures
from six.moves.http_client import OK, METHOD_NOT_ALLOWED, BAD_REQUEST
from gramex.handlers.twitterresthandler import NETWORK_TIMEOUT
from . import server, TestGramex

threadpool = concurrent.futures.ThreadPoolExecutor(8)


def async_fetch(name, path, method='post', url='/api/twitter/', **kwargs):
    future = threadpool.submit(getattr(requests, method), server.base_url + url + path, **kwargs)
    setattr(future, 'name', name)
    return future


class TestTwitterRESTHandler(TestGramex):
    'Test TwitterRESTHandler'

    def test_twitter(self):
        search = {'q': 'gramener', 'count': 2}
        tweets = {'screen_name': 'gramener', 'count': 2}
        tests = {
            'bad-request': {'path': 'search/tweets.json'},
            'search-url': {'path': 'search/tweets.json', 'params': search},
            'search-body': {'path': 'search/tweets.json', 'data': search},
            'show': {'path': 'users/show.json', 'data': tweets},
            'timeline': {'path': 'statuses/user_timeline.json', 'data': tweets},
            'get-ok': {'method': 'get', 'url': '/api/twitter-get/', 'path': 'search/tweets.json',
                       'data': search},
            'get-fail': {'method': 'get', 'path': 'search/tweets.json', 'data': search},
            'post-fail': {'method': 'post', 'url': '/api/twitter-get/',
                          'path': 'search/tweets.json', 'data': search},
        }
        # Fetch the tweets upfront, asynchronously
        futures = [async_fetch(name, **kwargs) for name, kwargs in tests.items()]
        done, not_done = concurrent.futures.wait(futures)
        response = {future.name: future.result() for future in done}

        self.assertEqual(response['bad-request'].status_code, BAD_REQUEST)
        for key in ('search-url', 'search-body', 'show', 'timeline', 'get-ok'):
            r = response[key]
            if r.status_code == NETWORK_TIMEOUT:
                continue
            self.assertEqual(r.status_code, OK)
            result = r.json()
            if key in ('search-url', 'search-body'):
                self.assertEqual(len(result['statuses']), 2)
            elif key == 'show':
                self.assertEqual(result['screen_name'].lower(), 'gramener')
            elif key == 'timeline':
                self.assertEqual(len(result), 2)
                self.assertEqual(result[0]['user']['screen_name'].lower(), 'gramener')

        self.assertEqual(response['get-fail'].status_code, METHOD_NOT_ALLOWED)
        self.assertEqual(response['post-fail'].status_code, METHOD_NOT_ALLOWED)
