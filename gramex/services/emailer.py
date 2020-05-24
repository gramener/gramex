import os
import smtplib
from six import string_types
from email import encoders
from mimetypes import guess_type
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.utils import formataddr, getaddresses
from gramex import console
from gramex.config import app_log


class SMTPMailer(object):
    '''
    Creates an object capable of sending HTML emails. Usage::

        >>> mailer = SMTPMailer(type='gmail', email='gramex.guide@gmail.com', password='...')
        >>> mailer.mail(
        ... to='person@example.com',
        ... subject='Subject',
        ... html='<strong>Bold text</strong>. <img src="cid:logo">'
        ... body='This plain text is shown if the client cannot render HTML',
        ... attachments=['1.pdf', '2.txt'],
        ... images={'logo': '/path/to/logo.png'})

    To test emails without sending them, add a ``stub=True`` option. This queues
    email info into the ``SMTPStub.stubs`` list without sending it. To print the
    email contents after sending it, use `stub='log'`.
    '''
    clients = {
        'gmail': {'host': 'smtp.gmail.com'},
        'yahoo': {'host': 'smtp.mail.yahoo.com'},
        'live': {'host': 'smtp.live.com'},
        'mandrill': {'host': 'smtp.mandrillapp.com'},
        'office365': {'host': 'smtp.office365.com'},
        'outlook': {'host': 'smtp-mail.outlook.com'},
        'icloud': {'host': 'smtp.mail.me.com'},
        'mail.com': {'host': 'smtp.mail.com'},
        'smtp': {'tls': False},
        'smtps': {},
    }
    # SMTP port, depending on whether TLS is True or False
    ports = {
        True: 587,
        False: 25
    }

    def __init__(self, type, email=None, password=None, stub=False, **kwargs):
        # kwargs: host, port, tls
        self.type = type
        self.email = email
        self.password = password
        self.stub = stub
        if type not in self.clients:
            raise ValueError('Unknown email type: %s' % type)
        self.client = self.clients[type]
        self.client.update(kwargs)
        if 'host' not in self.client:
            raise ValueError('Missing SMTP host')

    def mail(self, **kwargs):
        '''
        Sends an email. It accepts any email parameter in RFC 2822
        '''
        sender = kwargs.get('sender', self.email)
        # SES allows restricting the From: address. https://amzn.to/2Kqwh2y
        # Mailgun suggests From: be the same as Sender: http://bit.ly/2tGS5wt
        kwargs.setdefault('from', sender)
        to = recipients(**kwargs)
        msg = message(**kwargs)
        tls = self.client.get('tls', True)
        # Test cases specify stub: true. This uses a stub that logs emails
        if self.stub:
            server = SMTPStub(self.client['host'], self.client.get('port', self.ports[tls]),
                              self.stub)
        else:
            server = smtplib.SMTP(self.client['host'], self.client.get('port', self.ports[tls]))
        if tls:
            server.starttls()
        if self.email is not None and self.password is not None:
            server.login(self.email, self.password)
        server.sendmail(sender, to, msg.as_string())
        server.quit()
        app_log.info('Email sent via %s (%s) to %s', self.client['host'], self.email,
                     ', '.join(to))


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
    Some common message header keys are ``to``, ``cc``, ``bcc``, ``subject``,
    ``reply_to``, and ``on_behalf_of``. The values must be strings.

    Here are some examples::

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
            msg = html_part = MIMEText(html.encode('utf-8'), 'html', 'utf-8')
        else:
            msg = html_part = MIMEMultipart('related')
            html_part.attach(MIMEText(html.encode('utf-8'), 'html', 'utf-8'))
            for name, path in images.items():
                with open(path, 'rb') as handle:
                    img = MIMEImage(handle.read())
                    img.add_header('Content-ID', '<%s>' % name)
                    html_part.attach(img)
    if body and html:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(body.encode('utf-8'), 'plain', 'utf-8'))
        msg.attach(html_part)
    elif not html:
        msg = MIMEText((body or '').encode('utf-8'), 'plain', 'utf-8')

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
                           filename=os.path.basename(filename))
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


class SMTPStub(object):
    '''A minimal test stub for smtplib.SMTP with features used in this module'''
    stubs = []

    def __init__(self, host, port, options):
        # Maintain a list of all stub info so far
        self.options = options
        self.info = {}
        self.stubs.append(self.info)
        self.info.update(host=host, port=port)

    def starttls(self):
        self.info.update(starttls=True)

    def login(self, email, password):
        self.info.update(email=email, password=password)

    def sendmail(self, from_addr, to_addrs, msg):
        self.info.update(from_addr=from_addr, to_addrs=to_addrs, msg=msg)

    def quit(self):
        self.info.update(quit=True)
        if self.options == 'log':
            console('From: %s' % self.info['from_addr'])
            console('To: %s' % self.info['to_addrs'])
            console(self.info['msg'])
