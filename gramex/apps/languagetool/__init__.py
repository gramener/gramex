"""Python wrappers for LanguageTool."""

import os.path as op
from urllib.parse import quote

from tornado.gen import coroutine, Return
from tornado.httpclient import AsyncHTTPClient

from gramex.cache import Subprocess
from gramex.config import variables

cmd = ['java', '-cp', 'languagetool-server.jar', 'org.languagetool.server.HTTPServer']


@coroutine
def start_languagetool(handler):
    """Start the languagetool server."""
    cwd = op.join(variables['GRAMEXDATA'], 'apps', 'LanguageTool-4.4')
    if not op.isdir(cwd):
        raise Exception('LanguageTool not correctly installed.')

    port = handler.get_argument('port', 8081)
    cmd.append('--port {}'.format(port))
    public = handler.get_argument('public', False)
    if public:
        cmd.append('--public')
    allow_origin = handler.get_argument('allow-origin', "*")
    cmd.append('"{}"'.format(allow_origin))

    proc = Subprocess(cmd, cwd=cwd, stream_stdout=[handler.write], buffer_size='line')
    _ = yield proc.wait_for_exit()


@coroutine
def grammar_check(handler):
    url = "http://localhost:{port}/v2/check?language=en-us&text={text}"
    client = AsyncHTTPClient()
    port, text = handler.parth_args
    result = yield client.fetch(url.format(port=port, text=quote(text)))
    raise Return(result.body)
