import six
import json
import gramex
import tornado.gen
from oauthlib import oauth1
from orderedattrdict import AttrDict
from tornado.web import HTTPError
from tornado.auth import TwitterMixin, FacebookGraphMixin
from tornado.httputil import url_concat, responses
from gramex.transforms import build_transform
from .basehandler import BaseHandler
from gramex.http import OK, BAD_REQUEST, CLIENT_TIMEOUT

custom_responses = {
    CLIENT_TIMEOUT: 'Client Timeout'
}


class SocialMixin(object):
    @classmethod
    def setup_social(cls, user_info, transform={}, methods=['post'], **kwargs):
        # Session key that stores the user info
        cls.user_info = user_info

        # Set up transforms
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
    def social_response(self, response):
        # Set response headers
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
        for header, header_value in self.conf.kwargs.get('headers', {}).items():
            self.set_header(header, header_value)

        # Transform content
        content = response.body
        if content and response.code == OK:
            content = yield gramex.service.threadpool.submit(self.transforms, content=content)
        # Convert to JSON if required
        if not isinstance(content, (six.binary_type, six.text_type)):
            content = json.dumps(content, ensure_ascii=True, separators=(',', ':'))
        raise tornado.gen.Return(content)

    def transforms(self, content):
        result = json.loads(content.decode('utf-8'))
        for transform in self.transform:
            for value in transform(result):
                result = value
        return result


class TwitterRESTHandler(BaseHandler, SocialMixin, TwitterMixin):
    '''
    Proxy for the Twitter 1.1 REST API via these ``kwargs``::

        pattern: /twitter/(.*)
        handler: TwitterRESTHandler
        kwargs:
            key: your-consumer-key
            secret: your-consumer-secret
            access_key: your-access-key         # Optional -- picked up from session
            access_secret: your-access-token    # Optional -- picked up from session
            methods: [get, post]                # HTTP methods to use for the API
            path: /search/tweets.json           # Freeze Twitter API request

    Now ``POST /twitter/search/tweets.json?q=gramener`` returns the same response
    as the Twitter REST API ``/search/tweets.json``.

    If you only want to expose a specific API, specify a ``path:``. It overrides
    the URL path. The query parameters will still work.

    By default, ``methods`` is POST, and GET logs the user in, storing the access
    token in the session for future use. But you can specify the ``access_...``
    values and set ``methods`` to ``[get, post]`` to use both GET and POST
    requests to proxy the API.
    '''
    @classmethod
    def setup(cls, **kwargs):
        super(TwitterRESTHandler, cls).setup(**kwargs)
        cls.setup_social('user.twitter', **kwargs)

    @tornado.gen.coroutine
    def run(self, path=None):
        args = {key: self.get_argument(key) for key in self.request.arguments}
        params = AttrDict(self.conf.kwargs)
        # update params with session parameters
        if any(k not in params for k in ('access_key', 'access_secret')):
            info = self.session.get(self.user_info, {})
            if info:
                params['access_key'] = info['access_token']['key']
                params['access_secret'] = info['access_token']['secret']
            else:
                raise HTTPError(BAD_REQUEST, reason='access token missing')

        client = oauth1.Client(
            client_key=params['key'],
            client_secret=params['secret'],
            resource_owner_key=params['access_key'],
            resource_owner_secret=params['access_secret'])
        endpoint = params.get('endpoint', 'https://api.twitter.com/1.1/')
        path = params.get('path', path)
        uri, headers, body = client.sign(url_concat(endpoint + path, args))
        http = self.get_auth_http_client()
        response = yield http.fetch(uri, headers=headers, raise_error=False)
        result = yield self.social_response(response)
        self.write(result)

    @tornado.gen.coroutine
    def get(self, path=None):
        if self.get_argument('oauth_token', None):
            self.session[self.user_info] = yield self.get_authenticated_user()
            self.redirect_next()
        else:
            self.save_redirect_page()
            yield self.authorize_redirect(callback_uri=self.request.protocol + "://" +
                                          self.request.host + self.request.uri)

    def _oauth_consumer_token(self):
        return dict(key=self.conf.kwargs['key'],
                    secret=self.conf.kwargs['secret'])


class FacebookGraphHandler(BaseHandler, SocialMixin, FacebookGraphMixin):
    '''
    Proxy for the Facebook Graph API via these ``kwargs``::

        pattern: /facebook/(.*)
        handler: FacebookGraphHandler
        kwargs:
            key: your-consumer-key
            secret: your-consumer-secret
            access_token: your-access-token     # Optional -- picked up from session
            methods: [get, post]                # HTTP methods to use for the API
            scope: read_stream,user_photos      # Permissions requested for the user
            path: /me/feed                      # Freeze Facebook Graph API request

    Now ``POST /facebook/me`` returns the same response as the Facebook Graph API
    ``/me``. To request specific access rights, specify the ``scope`` based on
    `permissions`_ required by the `Graph API`_.

    If you only want to expose a specific API, specify a ``path:``. It overrides
    the URL path. The query parameters will still work.

    By default, ``methods`` is POST, and GET logs the user in, storing the access
    token in the session for future use. But you can specify the ``access_token``
    values and set ``methods`` to ``[get, post]`` to use both GET and POST
    requests to proxy the API.

    .. _permissions: https://developers.facebook.com/docs/facebook-login/permissions
    .. _Graph API: https://developers.facebook.com/docs/graph-api/reference
    '''
    @classmethod
    def setup(cls, **kwargs):
        super(FacebookGraphHandler, cls).setup(**kwargs)
        cls.setup_social('user.facebook', **kwargs)

    @tornado.gen.coroutine
    def run(self, path=None):
        args = {key: self.get_argument(key) for key in self.request.arguments}
        if 'access_token' in self.conf.kwargs:
            args['access_token'] = self.conf.kwargs['access_token']
        else:
            info = self.session.get(self.user_info, {})
            if 'access_token' in info:
                args['access_token'] = info['access_token']
            else:
                raise HTTPError(BAD_REQUEST, reason='access token missing')

        uri = url_concat(self._FACEBOOK_BASE_URL + '/' + self.conf.kwargs.get('path', path), args)
        http = self.get_auth_http_client()
        response = yield http.fetch(uri, raise_error=False)
        result = yield self.social_response(response)
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(result)

    @tornado.gen.coroutine
    def get(self, path=None):
        redirect_uri = self.request.protocol + "://" + self.request.host + self.request.uri
        if self.get_argument('code', False):
            self.session[self.user_info] = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.conf.kwargs['key'],
                client_secret=self.conf.kwargs['secret'],
                code=self.get_argument('code'))
            self.redirect_next()
        else:
            self.save_redirect_page()
            scope = self.conf.kwargs.get('scope', 'read_stream')
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.conf.kwargs['key'],
                extra_params={'scope': scope})
