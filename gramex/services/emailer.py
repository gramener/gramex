import os
import smtplib
from email import encoders
from mimetypes import guess_type
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.utils import formataddr, getaddresses
from gramex.config import app_log
from typing import List, Union


class SMTPMailer:
    '''Creates an object capable of sending HTML emails.

    Examples:
        >>> mailer = SMTPMailer(type='gmail', email='gramex.guide@gmail.com', password='...')
        >>> mailer.mail(
        ... to='person@example.com',
        ... subject='Subject',
        ... html='<strong>Bold text</strong>. <img src="cid:logo">'
        ... body='This plain text is shown if the client cannot render HTML',
        ... attachments=['1.pdf', '2.txt'],
        ... images={'logo': '/path/to/logo.png'})
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
    ports = {True: 587, False: 25}

    def __init__(
        self,
        type: str,
        email: str = None,
        password: str = None,
        host: str = None,
        port: int = None,
        tls: bool = True,
        stub: str = None,
    ):
        '''
        Parameters:
            type: Email service type
            email: SMTP server login email ID
            password: SMTP server login email password
            host: SMTP server. Not required when a `type` is specified
            port: SMTP server port. Defaults to 25 for non-TLS, 587 for TLS
            tls: True to use TLS, False to use non-TLS
            stub: 'log' prints email contents instead of sending it

        `type` can be:

        - `gmail`: Google Mail (smtp.gmail.com)
        - `yahoo`: Yahoo Mail (smtp.mail.yahoo.com)
        - `live`: Live.com mail (smtp.live.com)
        - `mandrill`: Mandrill (smtp.mandrillapp.com)
        - `office365`: Office 365 (smtp.office365.com)
        - `outlook`: Outlook (smtp-mail.outlook.com)
        - `icloud`: Apple iCloud (smtp.mail.me.com)
        - `mail`.com: Mail.com (smtp.mail.com)
        - `smtp`: Use ANY SMTP server via `host=`. tls=False by default
        - `smtps`: Use ANY SMTP server via `host=`. tls=True by default

        To test emails without sending them, use `stub=True` option. This queues email info into
        `SMTPStub.stubs` without sending it. Use `stub='log'` to print the email contents as well.
        '''
        self.type = type
        self.email = email
        self.password = password
        self.stub = stub
        if type not in self.clients:
            raise ValueError(f'Unknown email type: {type}')
        self.client = self.clients[type]
        for key, val in (('host', host), ('port', port), ('tls', tls)):
            if val is not None:
                self.client[key] = val
        if 'host' not in self.client:
            raise ValueError('Missing SMTP host')

    def mail(self, **kwargs):
        '''Sends an email.

        Examples:
            >>> mailer = SMTPMailer(type='gmail', email='gramex.guide@gmail.com', password='...')
            >>> mailer.mail(
            ... to='person@example.com',
            ... subject='Subject',
            ... html='<strong>Bold text</strong>. <img src="cid:logo">'
            ... body='This plain text is shown if the client cannot render HTML',
            ... attachments=['1.pdf', '2.txt'],
            ... images={'logo': '/path/to/logo.png'})
            >>> message(to='b@example.org', subject=sub, body=text, html=html)
            >>> message(to='b@example.org', subject=sub, body=text, attachments=['file.pdf'])
            >>> message(to='b@example.org', subject=sub, body=text, attachments=[
                    {'filename': 'test.txt', 'body': 'File contents'}
                ])
            >>> message(to='b@example.org', subject=sub, html='<img src="cid:logo">',
                        images={'logo': 'd:/images/logo.png'})

        Parameters may be any email parameter in [RFC 2822](https://www.rfc-wiki.org/wiki/RFC2822).
        Parameters are case insensitive. Most commonly used are:

        - `to`: The recipient email address
        - `cc`: The carbon copy recipient email address
        - `bcc`: The blind carbon copy recipient email address
        - `reply_to`: The reply-to email address
        - `on_behalf_of`: The sender email address
        - `subject`: The email subject
        - `body`: text content of the email
        - `html`: HTML content of the email. If both `html` and `body`
            are specified, the email contains both parts. Email clients may decide to
            show one or the other.
        - `attachments`: an list of file names or dict with:
            - `body`: a byte array of the content
            - `content_type`: MIME type or `filename` indicating the file name
        - `images`: dict of `{key: path}`.
            - `key` may be anything. The HTML should include the image via `<img src="cid:key">`
            - `path` is the absolute path to the image

        In addition, any keyword arguments passed are treated as message headers.

        `To`, `Cc` and `Bcc` may be:

        - a string with comma-separated emails, e.g. `'a@x.com, b@x.com'`
        - a list of strings with emails, e.g. `['a@x.com', 'b@x.com']`
        - a list of strings with comma-separated emails, e.g. `['a@x.com', 'b@x.com, c@x.com']`
        '''
        sender = kwargs.get('sender', self.email)
        # SES allows restricting the From: address. https://amzn.to/2Kqwh2y
        # Mailgun suggests From: be the same as Sender: http://bit.ly/2tGS5wt
        kwargs.setdefault('from', sender)
        # Identify recipients from to/cc/bcc fields.
        # Note: We MUST explicitly add EVERY recipient (to/cc/bcc) in sendmail(recipients=)
        to = recipients(**kwargs)
        msg = message(**kwargs)
        tls = self.client.get('tls', True)
        # Test cases specify stub: true. This uses a stub that logs emails
        if self.stub:
            server = SMTPStub(
                self.client['host'], self.client.get('port', self.ports[tls]), self.stub
            )
        else:
            server = smtplib.SMTP(self.client['host'], self.client.get('port', self.ports[tls]))
        if tls:
            server.starttls()
        if self.email is not None and self.password is not None:
            server.login(self.email, self.password)
        server.sendmail(sender, to, msg.as_string())
        server.quit()
        app_log.info(f'Email sent via {self.client["host"]} ({self.email}) to {", ".join(to)}')


def recipients(**kwargs):
    # Return all recipients from to/cc/bcc fields.
    # They may be comma-separated strings or lists of comma-separated strings.
    recipients = []
    for key in kwargs:
        if key.lower() in {'to', 'cc', 'bcc'}:
            to = kwargs[key]
            if isinstance(to, str):
                to = [to]
            # Format as RFC-822 formatted email addresses
            recipients += [formataddr(pair) for pair in getaddresses(to)]
    return recipients


def message(
    body: str = None,
    html: str = None,
    attachments: List[Union[str, dict]] = [],
    images: dict = {},
    **kwargs: dict,
):
    # Returns a MIME message object based on text or HTML content, and optional attachments.
    if html:
        if not images:
            msg = html_part = MIMEText(html.encode('utf-8'), 'html', 'utf-8')
        else:
            msg = html_part = MIMEMultipart('related')
            html_part.attach(MIMEText(html.encode('utf-8'), 'html', 'utf-8'))
            for name, path in images.items():
                with open(path, 'rb') as handle:
                    img = MIMEImage(handle.read())
                    img.add_header('Content-ID', f'<{name}>')
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
                with open(filename, 'rb') as handle:
                    content = handle.read()
                content_type = guess_type(filename, strict=False)[0]
            if content_type is None:
                content_type = 'application/octet-stream'
            maintype, subtype = content_type.split('/', 1)
            msg = MIMEBase(maintype, subtype)
            msg.set_payload(content)
            encoders.encode_base64(msg)
            msg.add_header(
                'Content-Disposition', 'attachment', filename=os.path.basename(filename)
            )
            msg_addon.attach(msg)
        msg = msg_addon

    # set headers
    for arg, value in kwargs.items():
        header = '-'.join(
            [
                # All SMTP headers are capitalised, except abbreviations
                w.upper() if w in {'ID', 'MTS', 'IPMS'} else w.capitalize()
                for w in arg.split('_')
            ]
        )
        msg[header] = _merge(value)

    return msg


def _merge(value):
    return ', '.join(value) if isinstance(value, list) else value


class SMTPStub:
    # A minimal test stub for smtplib.SMTP with features used in this module
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
            app_log.debug(f'From: {self.info["from_addr"]}')
            app_log.debug(f'To: {self.info["to_addrs"]}')
            app_log.debug(self.info['msg'])
