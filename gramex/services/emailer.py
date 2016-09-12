import smtplib
from email import encoders
from mimetypes import guess_type
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from gramex.config import app_log


class SMTPMailer(object):
    clients = {
        'gmail': {'host': 'smtp.gmail.com'},
        'yahoo': {'host': 'smtp.mail.yahoo.com'},
        'live': {'host': 'smtp.live.com'},
        'mandrill': {'host': 'smtp.mandrillapp.com'}
    }

    def __init__(self, type, email, password):
        self.type = type
        self.email = email
        self.password = password
        self.client = self.clients[type]

    def mail(self, **kwargs):
        sender = kwargs.get('sender', self.email)
        to = _merge(kwargs.get('to', self.email))
        msg = message(**kwargs)
        default_port = 587
        server = smtplib.SMTP(self.client['host'], self.client.get('port', default_port))
        server.starttls()
        server.login(self.email, self.password)
        server.sendmail(sender, to, msg.as_string())
        server.quit()
        app_log.info('Email sent via %s to %s', self.email, to)


def message(body=None, html=None, attachments=[], **kwargs):
    '''
    Returns a MIME message object based on text or HTML content, and optional
    attachments. It accepts 3 parameters:

    - ``body`` is the text content of the email
    - ``html`` is the HTML content of the email. If both ``html`` and ``body``
      are specified, the email contains both parts. Email clients may decide to
      show one or the other.
    - ``attachments`` is an array of file names or dicts. Each dict must have:
        - ``body`` -- a byte array of the content
        - ``content_type`` indicating the MIME type or ``filename`` indicating the file name

    In addition, any keyword arguments passed are treated as message headers.
    Some common message header keys are ``From``, ``To``, ``Cc``, ``Bcc``,
    ``Subject``, ``Reply-To``, and ``On-Behalf-Of``. The values must be strings.

    Here are some examples::

        >>> message(from='a@example.org', to='b@example.org', subject=sub, body=text)
        >>> message(to='b@example.org', subject=sub, body=text, html=html)
        >>> message(to='b@example.org', subject=sub, body=text, attachments=['file.pdf'])
        >>> message(to='b@example.org', subject=sub, body=text, attachments=[
                {'filename': 'test.txt', 'body': 'File contents'}
            ])
    '''
    if body and html:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(body, 'plain'))
        msg.attach(MIMEText(html, 'html'))
    elif html:
        msg = MIMEText(html, 'html')
    else:
        msg = MIMEText(body or '', 'plain')

    if attachments:
        msg_addon = MIMEMultipart()
        msg_addon.attach(msg)
        for doc in attachments:
            if isinstance(doc, dict):
                filename = doc.get('filename', 'data.bin')
                content_type = doc.get('content_type', guess_type(filename, strict=False)[0])
                content = doc['body']
            else:
                filename = doc
                content = open(filename, 'rb').read()
                content_type = guess_type(filename, strict=False)[0]
            if content_type is None:
                content_type = 'application/octet-stream'
            maintype, subtype = content_type.split('/', 1)
            msg = MIMEBase(maintype, subtype)
            msg.set_payload(content)
            encoders.encode_base64(msg)
            msg.add_header('Content-Disposition', 'attachment',
                           filename=filename)
            msg_addon.attach(msg)
        msg = msg_addon

    # set headers
    for arg, value in kwargs.items():
        header = '-'.join([
            # All SMTP headers are capitalised, except abbreviations
            w.upper() if w in {'ID', 'MTS', 'IPMS'} else w.capitalize()
            for w in arg.split('_')
        ])
        msg[header] = _merge(value)

    return msg


def _merge(value):
    return ', '.join(value) if isinstance(value, list) else value
