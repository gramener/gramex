import six
import gramex
import smtplib
import tornado.gen
from email import encoders
from mimetypes import guess_type
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase


class SMTPMailer(object):
    clients = {
        'gmail': {'domain': 'smtp.gmail.com', 'port': 587},
        'yahoo': {'domain': 'smtp.mail.yahoo.com', 'port': 587},
        'hotmail': {'domain': 'smtp.live.com', 'port': 587},
        'mandrill': {'domain': 'smtp.mandrillapp.com', 'port': 587}}

    def __init__(self, config):
        self.email = config.email
        self.password = config.password
        self.type = config.type

    @tornado.gen.coroutine
    def send_mail(self, to, sender=None, cc=[], bcc=[], reply_to=None,
                  subject='', body=None, attachments=[],
                  html=None, **kwargs):
        sender = sender or self.email
        msg = message(
            sender, to, cc=cc, bcc=bcc, reply_to=reply_to,
            subject=subject, body=body, attachments=attachments, html=html,
            **kwargs)
        response = yield gramex.service.threadpool.submit(
            self.connect, sender=sender, to=to,
            msg=msg)
        raise tornado.gen.Return(response)

    def connect(self, sender, to, msg):
        client = self.clients[self.type]
        server = smtplib.SMTP(client['domain'], client['port'])
        server.starttls()
        server.login(self.email, self.password)
        server.sendmail(sender, to, msg.as_string())
        server.quit()


def message(sender, to, cc=[], bcc=[], reply_to=None,
            subject='', body=None, attachments=[], html=None, **kwargs):
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

        msg['From'] = sender
        for k, v in six.iteritems({'To': to, 'Cc': cc, 'Bcc': bcc}):
            msg[k] = ', '.join(v) if isinstance(v, list) else v
        msg['Reply-To'] = reply_to
        msg['Subject'] = subject

        # set headers
        for arg, v in six.iteritems(kwargs):
            msg[arg.replace('_', '-')] = v

        return msg
