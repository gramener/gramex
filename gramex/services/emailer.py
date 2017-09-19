from __future__ import unicode_literals

import smtplib
from six import string_types
from email import encoders
from mimetypes import guess_type
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.utils import formataddr, getaddresses
from gramex.config import app_log


class SMTPMailer(object):
    '''
    Creates an object capable of sending HTML emails.
    '''
    clients = {
        'gmail': {'host': 'smtp.gmail.com'},
        'yahoo': {'host': 'smtp.mail.yahoo.com'},
        'live': {'host': 'smtp.live.com'},
        'mandrill': {'host': 'smtp.mandrillapp.com'}
    }

    def __init__(self, type, email, password, **kwargs):
        self.type = type
        self.email = email
        self.password = password
        self.client = self.clients.get(type, {})
        self.client.update(kwargs)
        if 'host' not in self.client:
            raise ValueError('Missing SMTP host')

    def mail(self, **kwargs):
        '''
        Sends an email. It accepts any email parameter in RFC 2822
        '''
        sender = kwargs.get('sender', self.email)
        to = recipients(**kwargs)
        msg = message(**kwargs)
        default_port = 587
        server = smtplib.SMTP(self.client['host'], self.client.get('port', default_port))
        server.starttls()
        server.login(self.email, self.password)
        server.sendmail(sender, to, msg.as_string())
        server.quit()
        app_log.info('Email sent via %s to %s', self.email, to)


def recipients(**kwargs):
    '''
    Returns a list of RFC-822 formatted email addresses given:

    - a string with comma-separated emails
    - a list of strings with emails
    - a list of strings with comma-separated emails
    '''
    recipients = []
    for key in kwargs:
        if key.lower() in {'to', 'cc', 'bcc'}:
            to = kwargs[key]
            if isinstance(to, string_types):
                to = [to]
            recipients += [formataddr(pair) for pair in getaddresses(to)]
    return recipients


def message(body=None, html=None, attachments=[], images={}, **kwargs):
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
    - ``images`` is a dict of ``{key: path}``. ``key`` may be anything. ``path``
      is an absolute path. The HTML can show the image by including
      ``<img src="cid:key">``

    In addition, any keyword arguments passed are treated as message headers.
    Some common message header keys are ``from``, ``to``, ``cc``, ``bcc``,
    ``subject``, ``reply_to``, and ``on_behalf_of``. The values must be strings.

    Here are some examples::

        >>> message(from='a@example.org', to='b@example.org', subject=sub, body=text)
        >>> message(to='b@example.org', subject=sub, body=text, html=html)
        >>> message(to='b@example.org', subject=sub, body=text, attachments=['file.pdf'])
        >>> message(to='b@example.org', subject=sub, body=text, attachments=[
                {'filename': 'test.txt', 'body': 'File contents'}
            ])
        >>> message(to='b@example.org', subject=sub, html='<img src="cid:logo">',
                    images={'logo': 'd:/images/logo.png'})
    '''
    if html:
        if not images:
            msg = html_part = MIMEText(html, 'html')
        else:
            msg = html_part = MIMEMultipart('related')
            html_part.attach(MIMEText(html, 'html'))
            for name, path in images.items():
                with open(path, 'rb') as handle:
                    img = MIMEImage(handle.read())
                    img.add_header('Content-ID', '<%s>' % name)
                    html_part.attach(img)
    if body and html:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(body, 'plain'))
        msg.attach(html_part)
    elif not html:
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
