import io
from gramex.handlers import BaseHandler

_mime = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'


class PPTXHandler(BaseHandler):
    def get(self):
        # pptgen is not required unless PPTXHandler is used
        from gramex.pptgen import pptgen        # noqa

        target = io.BytesIO()
        pptgen(target=target, handler=self, **self.kwargs)

        # Set up headers
        headers = self.kwargs.get('headers', {})
        headers.setdefault('Content-Type', _mime)
        for key, val in headers.items():
            self.set_header(key, val)

        self.write(target.getvalue())
