from __future__ import unicode_literals

import re
import os
import six
import json
import time
import shlex
import atexit
import psutil
import requests
import tornado.gen
from orderedattrdict import AttrDict
from threading import Thread, Lock
from subprocess import Popen, PIPE, STDOUT      # nosec
from six.moves.urllib.parse import urlencode, urljoin
from tornado.web import HTTPError
from tornado.httpclient import AsyncHTTPClient
from gramex.config import app_log, variables, recursive_encode
from gramex.http import OK, GATEWAY_TIMEOUT, BAD_GATEWAY, CLIENT_TIMEOUT
from .basehandler import BaseHandler

_PPTX_MIME = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
# HTTP headers not to forward to chromecapture.js.
# Keep this sync-ed with the same list in chromecapture.js
_IGNORE_HEADERS = {
    'host',             # The URL will determine the host
    'connection',       # Let Tornado manage the connection
    'upgrade',          # .. and the upgrades
    'content-length',   # The new request will have a different content - length
    'content-md5',      # ... and different content - md5
}


class Capture(object):
    default_port = 9900         # Default port to run CaptureJS at
    check_interval = 0.05       # Frequency (seconds) to check if self.started
    # Set engine configurations for PhantomJS and Puppeteer
    engines = AttrDict(
        phantomjs=AttrDict(
            cmd='phantomjs --ssl-protocol=any',
            script='capture.js',
            first_line=b'PhantomJS.*capture\\.js',
            name='Capture',
            version='1.0'
        ),
        chrome=AttrDict(
            cmd='node',
            script='chromecapture.js',
            first_line=b'node\\.js.*chromecapture\\.js',
            name='ChromeCapture',
            version='1.1'
        ),
    )

    '''
    Create a proxy for capture.js. Typical usage::

        capture = Capture()
        with open('screenshot.png', 'wb') as handle:
            handle.write(capture.png('https://gramener.com/'))
        with open('screenshot.pdf', 'wb') as handle:
            handle.write(capture.pdf('https://gramener.com/'))

    The constructor accepts these optional parameters:

    :arg int port: port where capture.js is running. Default: 9900
    :arg string url: URL:port where PhantomJS is running with capture.js.
        Default: ``http://localhost:<port>/``
    :arg string cmd: Command to run PhantomJS with capture.js at the specified
        port. Default: ``phantomjs $GRAMEXPATH/apps/capture/capture.js --port=<port>``
    :arg int timeout: Seconds to wait for PhantomJS to timeout. Default: 10

    The constructor runs :meth:`Capture.start` in a new thread, which checks if
    capture.js is running at ``url``. If not, it runs ``cmd`` and checks again.
    Until capture.js is detected, all capture methods will fail.
    '''
    def __init__(self, port=None, url=None, engine=None, cmd=None, timeout=10):
        # Set default values for port, url and cmd
        self.engine = self.engines['phantomjs' if engine is None else engine]
        port = self.default_port if port is None else port
        if url is None:
            url = 'http://localhost:%d/' % port
            if cmd is None:
                script = os.path.join(variables.GRAMEXPATH, 'apps', 'capture', self.engine.script)
                cmd = '%s "%s" --port=%d' % (self.engine.cmd, script, port)
        self.url = url
        self.first_line_re = re.compile(self.engine.first_line)
        self.cmd = cmd
        self.timeout = timeout
        self.browser = AsyncHTTPClient()
        self.lock = Lock()
        self.started = False
        self.start()

    def start(self):
        '''
        Starts a thread and check if capture is already running at ``url``. If
        not, start ``cmd`` and check again. Print logs from ``cmd``.

        This method is thread-safe. It may be called as often as required.
        :class:`CaptureHandler` calls this method if ``?start`` is passed.
        '''
        with self.lock:
            thread = Thread(target=self._start)
            thread.daemon = True
            thread.start()

    def _start(self):
        '''
        Check if capture is already running at ``url``. If not, start ``cmd``
        and check again. Print logs from ``cmd``.
        '''
        self.started = False
        script = self.engine.script
        try:
            # Check if capture.js is at the url specified
            app_log.info('Pinging %s at %s', script, self.url)
            r = requests.get(self.url, timeout=self.timeout)
            self._validate_server(r)
            self.started = True
        except requests.ReadTimeout:
            # If capture.js doesn't respond immediately, we haven't started
            app_log.error('url: %s timed out', self.url)
        except requests.ConnectionError:
            # Try starting the process again
            app_log.info('Starting %s via %s', script, self.cmd)
            self.close()
            # self.cmd is taken from the YAML configuration. Safe to run
            self.proc = Popen(shlex.split(self.cmd), stdout=PIPE, stderr=STDOUT)    # nosec
            self.proc.poll()
            atexit.register(self.close)
            # TODO: what if readline() does not return quickly?
            line = self.proc.stdout.readline().strip()
            if not self.first_line_re.search(line):
                return app_log.error('cmd: %s invalid. Returned "%s"', self.cmd, line)
            app_log.info('Pinging %s at %s', script, self.url)
            try:
                r = requests.get(self.url, timeout=self.timeout)
                self._validate_server(r)
                pid = self.proc.pid
                app_log.info(line.decode('utf-8') + ' live (pid=%s)', pid)
                self.started = True
                # Keep logging capture.js output until proc is killed by another thread
                while hasattr(self, 'proc'):
                    line = self.proc.stdout.readline().strip()
                    if len(line) == 0:
                        app_log.info('%s terminated: pid=%d', script, pid)
                        self.started = False
                        break
                    # Capture won't print anything, unless there's a problem, or if debug is on.
                    # So log it at warning level not info.
                    app_log.warning(line.decode('utf-8'))
            except Exception:
                app_log.exception('Ran %s. But %s not at %s', self.cmd, script, self.url)
        except Exception:
            app_log.exception('Cannot start Capture')

    def close(self):
        '''Stop capture.js if it has been started by this object'''
        if hasattr(self, 'proc'):
            try:
                process = psutil.Process(self.proc.pid)
                for proc in process.children(recursive=True):
                    proc.kill()
                process.kill()
            except psutil.NoSuchProcess:
                app_log.info('%s PID %d already killed', self.engine.script, self.proc.pid)
                pass
            delattr(self, 'proc')

    def _validate_server(self, response):
        # Make sure that the response we got is from the right version of capture.js
        server = response.headers.get('Server', '')
        parts = server.split('/', 2)
        script = self.engine.script
        if not len(parts) == 2 or parts[0] != self.engine.name or parts[1] < self.engine.version:
            raise RuntimeError('Server: %s at %s is not %s' % (server, self.url, script))

    @tornado.gen.coroutine
    def capture_async(self, headers=None, **kwargs):
        '''
        Returns a screenshot of the URL. Runs asynchronously in Gramex. Arguments
        are same as :py:func:`capture`
        '''
        # If ?start is provided, start server and wait until timeout
        if 'start' in kwargs:
            self.start()
            end_time = time.time() + self.timeout
            while not self.started and time.time() < end_time:
                yield tornado.gen.sleep(self.check_interval)
        if not self.started:
            raise RuntimeError('%s not started. See logs' % self.engine.script)
        if six.PY2:
            recursive_encode(kwargs)
        r = yield self.browser.fetch(
            self.url, method='POST', body=urlencode(kwargs, doseq=True), raise_error=False,
            connect_timeout=self.timeout, request_timeout=self.timeout, headers=headers)
        if r.code == OK:
            self._validate_server(r)
        raise tornado.gen.Return(r)

    def capture(self, url, **kwargs):
        '''
        Return a screenshot of the URL.

        :arg str url: URL to take a screenshot of
        :arg str ext: format of output. Can be pdf, png, gif or jpg
        :arg str selector: Restrict screenshot to (optional) CSS selector in URL
        :arg int delay: milliseconds (or expression) to wait for before taking a screenshot
        :arg str format: A3, A4, A5, Legal, Letter or Tabloid. Defaults to A4. For PDF
        :arg str layout: A3, A4, A5, Legal, 16x9, 16x10, 4x3. Defaults to 4x3. For PPTX
        :arg str orientation: portrait or landscape. Defaults to portrait. For PDF
        :arg str header: header for the page. For PDF
        :arg str footer: footer for the page. For PDF
        :arg int width: screen width. Default: 1200. For PNG/GIF/JPG
        :arg int height: screen height. Default: 768. For PNG/GIF/JPG
        :arg float scale: zooms the screen by a factor. For PNG/GIF/JPG
        :arg int dpi: dots (pixels) per inch. For PPTX
        :arg str title: slide title. For PPTX
        :arg int debug: sets log level for HTTP requests (2) and responses (1)
        :return: a bytestring with the binary contents of the screenshot
        :rtype: bytes
        :raises RuntimeError: if capture.js is not running or fails
        '''
        # Ensure that we're connecting to the right version of capture.js
        if not self.started:
            end_time = time.time() + self.timeout
            while not self.started and time.time() < end_time:
                time.sleep(self.check_interval)
            if not self.started:
                raise RuntimeError('%s not started. See logs' % self.engine.script)
        kwargs['url'] = url
        r = requests.post(self.url, data=kwargs, timeout=self.timeout)
        if r.status_code == OK:
            self._validate_server(r)
            return r.content
        else:
            raise RuntimeError('%s error: %s' % (self.engine.script, r.content))

    def pdf(self, url, **kwargs):
        '''An alias for :meth:`Capture.capture` with ``ext='pdf'``.'''
        kwargs['ext'] = 'pdf'
        return self.capture(url, **kwargs)

    def png(self, url, **kwargs):
        '''An alias for :meth:`Capture.capture` with ``ext='png'``.'''
        kwargs['ext'] = 'png'
        return self.capture(url, **kwargs)

    def pptx(self, url, **kwargs):
        '''An alias for :meth:`Capture.capture` with ``ext='pptx'``.'''
        kwargs['ext'] = 'pptx'
        return self.capture(url, **kwargs)

    def jpg(self, url, **kwargs):
        '''An alias for :meth:`Capture.capture` with ``ext='jpg'``.'''
        kwargs['ext'] = 'jpg'
        return self.capture(url, **kwargs)

    def gif(self, url, **kwargs):
        '''An alias for :meth:`Capture.capture` with ``ext='gif'``.'''
        kwargs['ext'] = 'gif'
        return self.capture(url, **kwargs)


class CaptureHandler(BaseHandler):
    '''
    Renders a web page as a PDF or as an image. It accepts the same arguments as
    :class:`Capture`.

    The page is called with the same args as :meth:`Capture.capture`. It also
    accepts a ``?start`` parameter that restarts capture.js if required.
    '''
    # Each config maps to a Capture() object. cls.captures[config] = Capture()
    captures = {}

    @classmethod
    def setup(cls, port=None, url=None, engine=None, cmd=None, **kwargs):
        super(CaptureHandler, cls).setup(**kwargs)
        capture_kwargs = {}
        for kwarg in ('timeout', ):
            if kwarg in kwargs:
                capture_kwargs[kwarg] = kwargs.pop(kwarg)
        # Create a new Capture only if the config has changed
        config = dict(engine=engine, port=port, url=url, cmd=cmd, **capture_kwargs)
        config_str = json.dumps(config, separators=[',', ':'], sort_keys=True)
        if config_str not in cls.captures:
            cls.captures[config_str] = cls.capture = Capture(**config)
        else:
            cls.capture = cls.captures[config_str]
        # TODO: if the old config is no longer used, close it
        cls.ext = {
            'pdf': dict(mime='application/pdf'),
            'png': dict(mime='image/png'),
            'jpg': dict(mime='image/jpeg'),
            'jpeg': dict(mime='image/jpeg'),
            'gif': dict(mime='image/gif'),
            'pptx': dict(mime=_PPTX_MIME),
        }

    @tornado.gen.coroutine
    def get(self):
        args = self.argparse(
            url={'default': self.request.headers.get('Referer', None)},
            ext={'choices': self.ext, 'default': 'pdf'},
            file={'default': 'screenshot'},
            selector={'nargs': '*'},
            cookie={},
            delay={},
            width={'type': int},
            height={'type': int},
            x={'type': int},
            y={'type': int},
            scale={'type': float},
            dpi={'type': int, 'nargs': '*'},
            format={'choices': ['A3', 'A4', 'A5', 'Legal', 'Letter', 'Tabloid'], 'default': 'A4'},
            layout={'choices': ['A3', 'A4', 'Letter', '16x9', '16x10', '4x3'], 'default': '4x3'},
            orientation={'choices': ['portrait', 'landscape'], 'default': 'portrait'},
            title={'nargs': '*'},
            title_size={'type': int, 'nargs': '*'},
            start={'nargs': '*'},
            debug={'nargs': '*'},
        )
        if args['url'] is None:
            self.write('Missing ?url=')
            raise tornado.gen.Return()

        # If the URL is a relative URL, treat it relative to the called path
        args['url'] = urljoin(self.request.full_url(), args['url'])
        # Copy all relevant HTTP headers as-is
        args['headers'] = {
            key: val for key, val in self.request.headers.items()
            if key not in _IGNORE_HEADERS
        }
        if 'cookie' not in args:
            cookie = self.request.headers.get('Cookie', None)
            if cookie is not None:
                args['cookie'] = cookie
        info = self.ext[args.ext]
        try:
            response = yield self.capture.capture_async(**args)
        except RuntimeError as e:
            # capture.js could not fetch the response
            raise HTTPError(BAD_GATEWAY, reason=e.args[0])

        if response.code == OK:
            self.set_header('Content-Type', info['mime'])
            self.set_header('Content-Disposition',
                            'attachment; filename="{file}.{ext}"'.format(**args))
            self.write(response.body)
        elif response.code == CLIENT_TIMEOUT:
            self.set_status(GATEWAY_TIMEOUT, reason='Capture is busy')
            self.set_header('Content-Type', 'application/json')
            self.write({'status': 'fail', 'msg': [
                'Capture did not respond within timeout: %ds' % self.capture.timeout]})
        else:
            self.set_status(response.code, reason='capture.js error')
            self.set_header('Content-Type', 'application/json')
            self.write(response.body)
