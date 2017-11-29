import os
import random
from unittest import TestCase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from gramex.services.emailer import message, recipients, SMTPMailer
from nose.tools import eq_, assert_raises

folder = os.path.dirname(os.path.abspath(__file__))


class TestEmailer(TestCase):
    def eq(self, msg1, msg2):
        '''Compare 2 messages ensuring random boundary values are the same'''
        random.seed(0)
        msg1 = msg1.as_string()
        random.seed(0)
        msg2 = msg2.as_string()
        eq_(msg1, msg2)

    def test_recipients(self):
        def msg_eq(src, result):
            eq_(set(src), set(result))
        msg_eq(recipients(to='a@z'), ['a@z'])
        msg_eq(recipients(to='a@z,b@z'), ['a@z', 'b@z'])
        msg_eq(recipients(to=['a@z', 'b@z']), ['a@z', 'b@z'])
        msg_eq(recipients(to=['a@z,b@z', 'c@z']), ['a@z', 'b@z', 'c@z'])
        msg_eq(recipients(to='A <a@z>'), ['A <a@z>'])
        msg_eq(recipients(to='A <a@z>, B <b@z>'), ['A <a@z>', 'B <b@z>'])
        msg_eq(recipients(to='a@z,b@z', Cc='c@z'), ['a@z', 'b@z', 'c@z'])
        msg_eq(recipients(to='a@z', Cc='b@z,c@z'), ['a@z', 'b@z', 'c@z'])
        msg_eq(recipients(To='a@z', Bcc='b@z,c@z'), ['a@z', 'b@z', 'c@z'])
        msg_eq(recipients(TO='a@z', CC='b@z', BCC='c@z'), ['a@z', 'b@z', 'c@z'])

    def test_message(self):
        text = 'This is some text'
        html = '<h1>Heading</h1>\n<p>This is a paragraph</p>'
        msg = message(body=text)
        self.eq(message(body=text), MIMEText(text, 'plain'))
        self.eq(message(html=html), MIMEText(html, 'html'))

        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        self.eq(message(body=text, html=html), msg)

    def test_attachment(self):
        img = os.path.join(folder, 'small-image.jpg')
        self.check_attachment(img)

        with open(img, 'rb') as handle:
            contents = handle.read()
        self.check_attachment({'content_type': 'image/jpeg', 'body': contents})
        self.check_attachment({'filename': img, 'body': contents})

    def check_attachment(self, img):
        msg = message(body='text', attachments=[img])
        img_part = list(msg.walk())[-1]
        eq_(img_part.get_content_type(), 'image/jpeg')
        if 'filename' in img:
            eq_(img_part.get_filename(), os.path.basename(img['filename']))

    def test_images(self):
        html = '<img src="cid:logo">'
        img = os.path.join(folder, 'small-image.jpg')
        msg = MIMEMultipart('related')
        msg.attach(MIMEText(html, 'html'))
        with open(img, 'rb') as handle:
            img_part = MIMEImage(handle.read())
            img_part.add_header('Content-ID', '<logo>')
            msg.attach(img_part)
        self.eq(message(html=html, images={'logo': img}), msg)

    def test_smtpmailer(self):
        with assert_raises(ValueError):
            SMTPMailer(type='any')          # unknown type
        with assert_raises(ValueError):
            SMTPMailer(type='smtp')         # no host
        with assert_raises(ValueError):
            SMTPMailer(type='smtps')        # no host
        # These do not raise an error
        SMTPMailer(type='gmail', email='', password='')
        SMTPMailer(type='yahoo', email='', password='')
        SMTPMailer(type='live', email='', password='')
        SMTPMailer(type='mandrill', email='', password='')
        SMTPMailer(type='smtp', host='hostname')
        SMTPMailer(type='smtps', host='hostname')

        # TODO: using stubs, test that:
        # - the email is sent to the correct host, port, email, password in above cases
        # - test SMTP with and without password as well
        # - test SMTPS, custom ports
