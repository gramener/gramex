import json
import gramex
import tornado.gen
from oauthlib import oauth1
from orderedattrdict import AttrDict
from gramex.transforms import build_transform
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat, responses
from .basehandler import BaseHandler

custom_responses = {
    599: 'Network Timeout'
}


class TwitterRESTHandler(BaseHandler):
    @classmethod
    def setup(cls, **kwargs):
        super(TwitterRESTHandler, cls).setup(**kwargs)

        posttransform = kwargs.get('posttransform', {})
        cls.posttransform = []
        if 'function' in posttransform:
            cls.posttransform.append(
                build_transform(
                    posttransform, vars=AttrDict(content=None),
                    filename='url>%s' % cls.name))

    @tornado.gen.coroutine
    def post(self, path):
        args = {key: self.get_argument(key) for key in self.request.arguments}
        params = self.conf.kwargs
        client = oauth1.Client(
            params.consumer_key,
            client_secret=params.consumer_secret,
            resource_owner_key=params.access_token,
            resource_owner_secret=params.access_token_secret)
        endpoint = params.get('endpoint', 'https://api.twitter.com/1.1/')
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

        if response.body:
            kwargs = {'content': response.body}
            self.result = yield gramex.service.threadpool.submit(self.transforms, **kwargs)
            self.write(self.result)

    def transforms(self, content):
        result = json.loads(content)
        if not isinstance(result, dict):
            result = {'result': result}
        for posttransform in self.posttransform:
            for value in posttransform(result):
                result = value
        return result
