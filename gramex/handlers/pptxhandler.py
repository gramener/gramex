import io
import pptgen
from gramex.handlers import BaseHandler

_mime = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'


class PPTXHandler(BaseHandler):
    def get(self):
        target = io.BytesIO()
        pptgen.pptgen(target=target, handler=self, **self.kwargs)

        # Set up headers
        headers = self.kwargs.get('headers', {})
        headers.setdefault('Content-Type', _mime)
        for key, val in headers.items():
            self.set_header(key, val)

        self.write(target.getvalue())
