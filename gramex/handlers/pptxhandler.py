import io
from gramex.handlers import BaseHandler

_mime = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'


class PPTXHandler(BaseHandler):
    def get(self):
        # Load correct version of pptgen based on version:
        kwargs = dict(self.kwargs)
        version = kwargs.pop('version', None)
        if version == 2:
            from gramex.pptgen2 import pptgen

            kwargs['mode'] = 'expr'
        else:
            from gramex.pptgen import pptgen

        target = io.BytesIO()
        pptgen(target=target, handler=self, **kwargs)

        # Set up headers
        headers = kwargs.get('headers', {})
        headers.setdefault('Content-Type', _mime)
        for key, val in headers.items():
            self.set_header(key, val)

        self.write(target.getvalue())
