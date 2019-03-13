"""Python wrappers for LanguageTool."""

import os.path as op

from tornado.gen import coroutine, Return
from tornado.httpclient import AsyncHTTPClient

from gramex.cache import Subprocess
from gramex.config import variables

cmd = ['java', '-cp', 'languagetool-server.jar', 'org.languagetool.server.HTTPServer']


def start_languagetool():
    """Start the languagetool server."""
    cwd = op.join(variables['GRAMEXDATA'], 'apps', 'LanguageTool-4.4')
    if not op.isdir(cwd):
        raise Exception('LanguageTool not correctly installed.')

    port = variables.get('LT_PORT', 8081)
    cmd.append('--port {}'.format(port))
    public = variables.get('LT_PUBLIC', False)
    if public:
        cmd.append('--public')
    allow_origin = variables.get('LT_ALLOW_ORIGIN', "*")
    cmd.append('"{}"'.format(allow_origin))

    proc = Subprocess(cmd, cwd=cwd, buffer_size='line')
    out, err = yield proc.wait_for_exit()
    raise Return(out.decode('utf-8'))


@coroutine
def grammar_check(handler):
    url = "http://localhost:{port}/v2/check?language=en-us&text={text}"
    client = AsyncHTTPClient()
    port, text = handler.path_args
    result = yield client.fetch(url.format(port=port, text=text))
    raise Return(result.body)
