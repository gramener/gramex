from __future__ import unicode_literals
from . import TestGramex
from nose.tools import eq_, ok_


class TestSession(TestGramex):
    def test_sms_setup(self):
        info = self.get('/sms/info').json()
        sms = info['amazonsns']
        eq_(sms['cls'], 'AmazonSNS')
        eq_(sms['smstype'], 'Transactional')
        ok_('botocore.client.SNS' in sms['client'])
