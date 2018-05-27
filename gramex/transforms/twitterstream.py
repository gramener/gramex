from __future__ import unicode_literals

import os
import six
import json
import time
import datetime
import tornado.httpclient
import gramex
from oauthlib import oauth1
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.httputil import HTTPHeaders, parse_response_start_line
from six.moves.urllib_parse import urlencode
from gramex.config import app_log
from gramex.transforms import flattener, build_transform
from gramex.http import (RATE_LIMITED, TOO_MANY_REQUESTS, CLIENT_TIMEOUT,
                         INTERNAL_SERVER_ERROR, GATEWAY_TIMEOUT)


class TwitterStream(object):
    '''
    Starts a Twitter Streaming client. Sample usage::

        >>> from gramex.transforms import TwitterStream
        >>> stream = TwitterStream(
        ...     track='modi,mms',
        ...     path='save-as-file.json',
        ...     key='...',
        ...     secret='...',
        ...     access_key='...',
        ...     access_secret='...',
        ...     flush=True)

    This saves all tweets mentioning ``modi`` or ``mms`` in ``save-as-file.json``
    with each line representing a tweet in JSN format.

    If ``flush=True``, the file is flushed on every tweet. If ``flush=<number>``,
    the file is flushed every ``<number>`` seconds. If ``flush=False`` (default),
    the file is flushed only when the file or app is closed.

    This function runs forever, so run it in a separate thread.
    '''
    def __init__(self, **kwargs):
        self.params = kwargs
        self.url = 'https://stream.twitter.com/1.1/statuses/filter.json'
        self.valid_params = {
            'follow', 'track', 'locations', 'delimited', 'stall_warnings',
            'filter_level', 'language'}
        self.enabled = True
        self.delay = 0

        # Set up writers
        if 'path' in kwargs:
            self.stream = StreamWriter(kwargs['path'], flush=kwargs.get('flush', False))
            self.process_bytes = self.stream.write
        elif 'function' in kwargs:
            self.process_json = build_transform(
                kwargs, vars={'message': {}}, filename='TwitterStream:function')
        elif kwargs.get('driver') == 'sqlalchemy':
            engine = gramex.data.create_engine(kwargs['url'], **kwargs.get('parameters', {}))
            table = gramex.data.get_table(kwargs['table'])
            fields = kwargs['fields']
            for field in list(fields.keys()):
                if field not in table.columns:
                    app_log.error('TwitterStream field %s not in table' % field)
                    fields.pop(field)
            flatten = flattener(fields=fields)
            self.process_json = lambda tweet: engine.execute(table.insert(flatten(tweet)))

        self.buf = bytearray()
        self.client = tornado.httpclient.HTTPClient()
        while True:
            # Set .enabled to False to temporarily disable streamer
            if self.enabled:
                params = {key: val.encode('utf-8') for key, val in self.params.items()
                          if key in self.valid_params}
                if 'follow' not in params and 'track' not in params and 'locations' not in params:
                    self.enabled = False
                    self.delay = 5
                    app_log.error('TwitterStream needs follow, track or locations. Disabling')
                else:
                    self.fetch_tweets(params)
            # Restart after a delay determined by
            time.sleep(self.delay)

    def fetch_tweets(self, tweet_params):
        oauth = oauth1.Client(
            client_key=self.params['key'],
            client_secret=self.params['secret'],
            resource_owner_key=self.params['access_key'],
            resource_owner_secret=self.params['access_secret'])
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Gramex',
        }
        url, headers, data = oauth.sign(
            self.url, 'POST', body=urlencode(tweet_params), headers=headers)
        self.req = tornado.httpclient.HTTPRequest(
            method='POST', url=url, body=data, headers=headers,
            request_timeout=864000,      # Keep request alive for 10 days
            streaming_callback=self._stream,
            header_callback=self.header_callback)

        try:
            self.headers = None
            self.client.fetch(self.req)
            self.delay = 0
        except tornado.httpclient.HTTPError as e:
            # HTTPError is raised for non-200 HTTP status codes.
            # For rate limiting, start with 1 minute and double each attempt
            if e.code in {RATE_LIMITED, TOO_MANY_REQUESTS}:
                self.delay = self.delay * 2 if self.delay else 60
                app_log.error('TwitterStream HTTP %d (rate limited): %s. Retry: %ss',
                              e.code, e.response, self.delay)
            # For Tornado timeout errors, reconnect immediately
            elif e.code == CLIENT_TIMEOUT:
                self.delay = 0
                app_log.error('TwitterStream HTTP %d (timeout): %s. Retry: %ss',
                              e.code, e.response, self.delay)
            # For server errors, start with 5 seconds and double until 320 seconds
            elif INTERNAL_SERVER_ERROR <= e.code <= GATEWAY_TIMEOUT:
                self.delay = min(320, self.delay * 2 if self.delay else 1)      # noqa: 320 seconds
                app_log.error('TwitterStream HTTP %d: %s. Retry: %ss',
                              e.code, e.response, self.delay)
            # For client errors (e.g. wrong params), disable connection
            else:
                self.delay, self.enabled = 5, False
                app_log.error('TwitterStream HTTP %d: %s. Disabling', e.code, e.response)
        except Exception as e:
            # Other errors are possible, such as IOError.
            # Increase the delay in reconnects by 250ms each attempt, up to 16 seconds.
            self.delay = min(16, self.delay + 0.25)         # noqa: 16 seconds, 0.25 seconds
            app_log.error('TwitterStream exception %s. Retry: %ss', e, self.delay)

    def header_callback(self, line):
        try:
            if self.headers is None:
                start_line = parse_response_start_line(line)
                self.http_version, self.status_code, self.http_reason = start_line
                self.headers = HTTPHeaders()
            else:
                self.headers.parse_line(line)
        except Exception:
            app_log.exception('Cannot parse header %s' % line)

    def _stream(self, data):
        buf = self.buf
        buf.extend(data)
        while len(buf):
            index = buf.find(b'\r\n')
            if index < 0:
                break
            data = bytes(buf[:index])
            del buf[:index + 2]
            # Ignore stall warnings
            if len(data) == 0:
                continue
            try:
                self.process_bytes(data)
            except Exception:
                app_log.exception('TwitterStream could not process: %s' % data)

    def process_bytes(self, data):
        try:
            text = six.text_type(data, encoding='utf-8')
            message = json.loads(text)
        except UnicodeError:
            app_log.error('TwitterStream unicode error: %s', data)
            return
        except ValueError:
            # When rate limited, text="Exceeded connection limit for user"
            app_log.error('TwitterStream non-JSON data: %s', text)
            return
        # Process the message (which is usually, but not always, a tweet)
        try:
            self.process_json(message)
        except Exception:
            app_log.exception('TwitterStream could not process message: %s' % text)

    def process_json(self, message):
        '''Subclass this to process tweets differently'''
        app_log.info(repr(message))


class StreamWriter(object):
    def __init__(self, path, flush=False):
        self.path = path
        self.stream = self.stream_path = self.flush_on_write = None
        if isinstance(flush, bool):
            self.flush_on_write = flush
        elif isinstance(flush, (int, float)):
            self.flush_loop = PeriodicCallback(self.flush, flush * 1000)
            self.flush_loop.start()
        else:
            raise ValueError('flush=%r is not int/bool' % flush)
        self.rotate()

    def flush(self):
        if self.stream is not None:
            self.stream.flush()

    def rotate(self):
        '''
        Create and rotate file streams.

        The ``path`` format string determines the filename. For example,
        ``tweets.{:%Y-%m-%d}.jsonl`` creates a filename based on the current
        date, e.g. ``tweets.2016-12-31.jsonl``. When rotating, if the new
        filename is the same as the old, the file continues. If it's a different
        file, the old file is closed and the new file is created.

        The rotation frequency is based on the crontab entries in the config,
        i.e. based on ``hours``, ``days``, ``weeks``, etc. It defaults to every
        minute.
        '''
        # First, flush the stream to ensure that data is not lost.
        # Then set up new stream (if required, based on the filename)
        self.flush()
        path = self.path.format(datetime.datetime.utcnow())
        if path != self.stream_path:
            if self.stream is not None:
                self.stream.close()
            self.stream_path = path
            folder = os.path.dirname(os.path.abspath(path))
            if not os.path.exists(folder):
                os.makedirs(folder)
            self.stream = open(path, 'ab')
            app_log.debug('StreamWriter writing to %s', path)

        # Schedule the next call after a minute
        IOLoop.current().call_later(60, self.rotate)

    def write(self, data):
        self.stream.write(data)
        self.stream.write('\n')
        if self.flush_on_write:
            self.stream.flush()
