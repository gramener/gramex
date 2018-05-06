import os
import json
import logging
import gramex
from tornado.web import HTTPError
from gramex.http import BAD_REQUEST

folder = os.path.dirname(os.path.abspath(__file__))
template = os.path.join(folder, 'index.html')


def gramexupdate(handler):
    # When a user casually visits the page, render friendly output
    if handler.request.method == 'GET':
        return gramex.cache.open(template, 'template').generate(version=gramex.__version__)
    # Log all messages
    try:
        logs = json.loads(handler.request.body, encoding='utf-8')
        if not isinstance(logs, list):
            raise ValueError()
    except (ValueError, AssertionError):
        raise HTTPError(BAD_REQUEST, reason='Invalid POST data. Expecting JSON array')
    logger = logging.getLogger('gramexupdate')
    for log in logs:
        log['ip'] = handler.request.remote_ip
        logger.info(json.dumps(log, ensure_ascii=True, separators=(',', ':')))
    # Return the latest Gramex version
    return {'version': gramex.__version__}
