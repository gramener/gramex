import six
import json
import gramex
import tornado.gen
from oauthlib import oauth1
from orderedattrdict import AttrDict
from tornado.web import HTTPError
from tornado.auth import TwitterMixin
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat, responses
from gramex.transforms import build_transform
from .basehandler import BaseHandler

OK, BAD_REQUEST, NETWORK_TIMEOUT = 200, 400, 599
custom_responses = {
    NETWORK_TIMEOUT: 'Network Timeout'
}


class TwitterRESTHandler(BaseHandler, TwitterMixin):
    @classmethod
    def setup(cls, transform={}, methods=['post'], **kwargs):
        super(TwitterRESTHandler, cls).setup(**kwargs)

        # Twitter user information is stored in
        cls.twitter_info = 'user.twitter'
        cls.transform = []
        if 'function' in transform:
            cls.transform.append(build_transform(transform, vars=AttrDict(content=None),
                                                 filename='url>%s' % cls.name))
        if not isinstance(methods, list):
            methods = [methods]
        methods = set(method.lower().strip() for method in methods)
        for method in ('get', 'post', 'put', 'patch'):
            if method in methods:
                setattr(cls, method, cls.run)

    @tornado.gen.coroutine
    def run(self, path=None):
        args = {key: self.get_argument(key) for key in self.request.arguments}
        params = AttrDict(self.conf.kwargs)
        # update params with session parameters
        if any(k not in params for k in ('access_token', 'access_token_secret')):
            info = self.session.get(self.twitter_info, {})
            if info:
                params['access_token'] = info['access_token']['key']
                params['access_token_secret'] = info['access_token']['secret']
            else:
                raise HTTPError(BAD_REQUEST, reason='access_token missing')

        client = oauth1.Client(
            params.consumer_key,
            client_secret=params.consumer_secret,
            resource_owner_key=params.access_token,
            resource_owner_secret=params.access_token_secret)
        endpoint = params.get('endpoint', 'https://api.twitter.com/1.1/')
        path = params.get('path', path)
        uri, headers, body = client.sign(url_concat(endpoint + path, args))
        http_client = AsyncHTTPClient()
        response = yield http_client.fetch(uri, headers=headers, raise_error=False)

        # Set Twitter headers
        if response.code in responses:
            self.set_status(response.code)
        else:
            self.set_status(response.code, custom_responses.get(response.code))
        for header, header_value in response.headers.items():
            # We're OK with anything that starts with X-
            # Also set MIME type and last modified date
            if header.startswith('X-') or header in {'Content-Type', 'Last-Modified'}:
                self.set_header(header, header_value)

        # Set user's headers
        for header, header_value in params.get('headers', {}).items():
            self.set_header(header, header_value)

        content = response.body
        if content and response.code == OK:
            content = yield gramex.service.threadpool.submit(self.transforms, content=content)
        if not isinstance(content, (six.binary_type, six.text_type)):
            content = json.dumps(content, ensure_ascii=True, separators=(',', ':'))
        self.write(content)

    def transforms(self, content):
        result = json.loads(content.decode('utf-8'))
        for transform in self.transform:
            for value in transform(result):
                result = value
        return result

    @tornado.gen.coroutine
    def get(self, path=None):
        if self.get_argument('oauth_token', None):
            self.session[self.twitter_info] = yield self.get_authenticated_user()
            self.redirect_next()
        else:
            self.save_redirect_page()
            yield self.authorize_redirect(callback_uri=self.request.protocol + "://" +
                                          self.request.host + self.request.uri)

    def _oauth_consumer_token(self):
        return dict(key=self.conf.kwargs['consumer_key'],
                    secret=self.conf.kwargs['consumer_secret'])
