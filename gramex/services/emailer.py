import smtplib
import tornado.gen
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
        server = smtplib.SMTP(self.client['host'], self.client.get('port', 587))
        server.starttls()
        server.login(self.email, self.password)
        server.sendmail(sender, to, msg.as_string())
        server.quit()
        app_log.info('Email sent via %s to %s', self.email, to)


def message(body=None, html=None, attachments=[], **kwargs):
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
        for filename in attachments:
            content = open(filename, 'rb').read()
            content_type, encoding = guess_type(filename)
            if content_type is None or encoding is not None:
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
