from gramex.config import app_log
from requests import Request
from tornado.template import Template


REQUESTS = """{% autoescape None %}from requests import {{ method }}
response = {{ method }}("{{ url }}")
"""


def prep_requests(handler):
    method, url = handler.request.method, handler.get_argument("url")
    req = Request(method, url)
    prepped = req.prepare()
    python = Template(REQUESTS).generate(method=method.lower(), url=url).decode()

    try:
        from curlify import to_curl

        curl = to_curl(prepped)
    except ImportError:
        app_log.warning("Please pip install curlify to generate curl code.")
        curl = ""

    return {"curl": curl, "python": python}
