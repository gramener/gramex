from __future__ import unicode_literals

import os
import email
import gramex
import gramex.cache
from binascii import a2b_base64
from datetime import datetime, timedelta
from . import folder, utils, TestGramex
from .test_capturehandler import get_text
from nose.tools import eq_, ok_


def run_alert(name, count=1):
    '''Run named alert and return count mail results. If count is not 1, returns a list'''
    del utils.SMTPStub.stubs[:]
    utils.info.alert[name].run()
    eq_(len(utils.SMTPStub.stubs), count)
    if count == 1:
        return utils.SMTPStub.stubs[0]
    else:
        return utils.SMTPStub.stubs


class TestAlerts1(TestGramex):
    def test_startup(self):
        # Startup mails run without needing a trigger.
        # We have only 1 startup mail. There's a no-startup that SHOULD NOT run
        eq_(len(utils.SMTPStub.stubs), 1)
        # Check that the one startup mail is the right one
        mail = utils.SMTPStub.stubs[0]
        eq_(mail['to_addrs'], ['startup@example.org'])
        ok_('Subject: Gramex started\n' in mail['msg'])


class TestAlerts2(TestGramex):
    def test_errors(self):
        # If there's an email service, service: should default to the first one
        if len(utils.info.email.keys()) > 0:
            ok_('alert-no-service' in utils.info.alert)
        else:
            ok_('alert-no-service' not in utils.info.alert)

    def test_schedule(self):
        mail = run_alert('alert-schedule')
        # This schedule runs every hour
        next = utils.info.alert['alert-schedule'].cron.next(default_utc=False)
        now = datetime.now()
        next_hour = now + timedelta(hours=1)
        next_hour = next_hour.replace(minute=0, second=0, microsecond=0)
        diff = abs((now + timedelta(seconds=next)) - next_hour).total_seconds()
        ok_(diff < 0.5)
        # Test content
        eq_(mail['to_addrs'], ['admin@example.org'])
        ok_('Subject: Scheduled alert\n' in mail['msg'])

    def test_template(self):
        mail = run_alert('alert-template')
        obj = email.message_from_string(mail['msg'])
        eq_(obj['To'], 'user@example.org')
        eq_(obj['Cc'], 'cc@example.org')
        eq_(obj['Bcc'], 'bcc@example.org')
        eq_(obj['Subject'], 'subject')
        body, html = obj.get_payload()
        eq_(body.get_payload(decode=True).decode('utf-8'), 'body')
        eq_(html.get_payload(decode=True).decode('utf-8'), 'html')
        eq_(body['Content-Type'].split(';')[0], 'text/plain')
        eq_(html['Content-Type'].split(';')[0], 'text/html')

    def test_templatefile(self):
        mail = run_alert('alert-templatefile')
        obj = email.message_from_string(mail['msg'])
        eq_(obj['To'], 'user@example.org')
        body, html = obj.get_payload()
        eq_(body.get_payload(decode=True).decode('utf-8'), 'template-alert\n')
        eq_(html.get_payload(decode=True).decode('utf-8'), 'template-alert\n')
        eq_(body['Content-Type'].split(';')[0], 'text/plain')
        eq_(html['Content-Type'].split(';')[0], 'text/html')

    def test_markdown(self):
        mail = run_alert('alert-markdown')
        obj = email.message_from_string(mail['msg'])
        body, html = obj.get_payload()
        self.check_css(html.get_payload(decode=True).decode('utf-8'), ('h1', 'markdown'))

        mail = run_alert('alert-markdown-template')
        obj = email.message_from_string(mail['msg'])
        body, html = obj.get_payload()
        self.check_css(html.get_payload(decode=True).decode('utf-8'), ('h1', 'template-alert'))

    def test_attachments(self):
        mail = run_alert('alert-attachments')
        obj = email.message_from_string(mail['msg'])
        eq_(obj['To'], 'user@example.org')

        main, attachment = obj.get_payload()
        eq_(main['Content-Type'].split(';')[0], 'multipart/related')
        html, img = main.get_payload()
        eq_(html.get_payload(decode=True).decode('utf-8'), '<img src="cid:img">')
        eq_(img['Content-ID'], '<img>')
        with open(os.path.join(folder, 'sample.png'), 'rb') as handle:
            img_file = handle.read()
        eq_(a2b_base64(img.get_payload()), img_file)

        ok_(attachment['Content-Type'].split(';')[0] in
            {'application/x-zip-compressed', 'application/zip'})
        eq_(attachment['Content-Disposition'], 'attachment; filename="install-test.zip"')
        with open(os.path.join(folder, 'install-test.zip'), 'rb') as handle:
            zip_file = handle.read()
        eq_(a2b_base64(attachment.get_payload()), zip_file)

    def test_data(self):
        mail = run_alert('alert-data')
        obj = email.message_from_string(mail['msg'])
        eq_(obj['To'], 'user@example.org')

        data = gramex.cache.open(os.path.join(folder, 'actors.csv'))
        eq_(obj['Subject'], '%d actors from smtps_stub' % len(data))
        eq_(obj.get_payload(decode=True).decode('utf-8'), '%d votes' % data['votes'].sum())

    def test_condition(self):
        data = gramex.cache.open(os.path.join(folder, 'actors.csv'))
        subset = data[data['votes'] > 100]

        mail = run_alert('alert-condition-df')
        obj = email.message_from_string(mail['msg'])
        eq_(obj['To'], 'user@example.org')
        eq_(obj['Subject'], '%d actors' % len(subset))
        ok_(obj.get_payload(decode=True).decode('utf-8'), '%d votes' % subset['votes'].sum())

        run_alert('alert-condition-0', count=0)
        run_alert('alert-condition-false', count=0)

        mail = run_alert('alert-condition-dict')
        obj = email.message_from_string(mail['msg'])
        eq_(obj['To'], 'user@example.org, admin@example.org')
        eq_(obj['Subject'], '%d actors' % len(data))
        ok_(obj.get_payload(decode=True).decode('utf-8'), 'val is hello')

    def test_each(self):
        data = gramex.cache.open(os.path.join(folder, 'actors.csv'))
        cutoff = 100
        subset = data[data['votes'] > cutoff]

        mails = run_alert('alert-each', count=len(subset))
        for (index, row), mail in zip(subset.iterrows(), mails):
            obj = email.message_from_string(mail['msg'])
            eq_(obj['To'], row['name'].replace(' ', '_') + '@example.org')
            eq_(obj['Subject'], 'Congrats #%d! You got %d votes' % (index, row['votes']))
            # Check that the attachment has the user object (which is a template)
            main, attachment = obj.get_payload()
            text = get_text(a2b_base64(attachment.get_payload()))
            ok_(row['name'] in text)

        mails = run_alert('alert-data-inplace', count=2)
        fields = ['x@example.org', 'y@example.org']
        for field, mail in zip(fields, mails):
            obj = email.message_from_string(mail['msg'])
            eq_(obj['To'], field)
            eq_(obj['Subject'], field)
            eq_(obj.get_payload(decode=True).decode('utf-8'), 'Body is %s' % field)

    def test_capture(self):
        # alert-capture should run as user {id: login@example.org, role: manager}
        mail = run_alert('alert-capture')
        obj = email.message_from_string(mail['msg'])
        main, attachment = obj.get_payload()
        text = get_text(a2b_base64(attachment.get_payload()))
        ok_('login@example.org' in text)
        ok_('manager' in text)
        ok_('id=login@example.org, role=manager' in obj['Subject'])
