from __future__ import unicode_literals

import boto3
from gramex.config import app_log


class Notifier(object):
    def send(self, to, subject, sender):
        raise NotImplementedError()


class AmazonSNS(Notifier):
    '''
    Send messages via AmazonSNS::

        >>> notifier = AmazonSNS(
        ...     aws_access_key_id='...',
        ...     aws_secret_access_key='...',
        ...     region_name='ap-southeast-1',
        ...     smstype='Transactional')
        >>> notifier.send(
        ...     to='+919741552552',
        ...     from='gramex',
        ...     subject='This is the content of the message')
    '''

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 smstype='Transactional', **kwargs):
        self.client = boto3.client(
            'sns',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            **kwargs)
        self.smstype = smstype

    def send(self, to, subject, sender):
        result = self.client.publish(
            PhoneNumber=to,
            Message=subject,
            MessageAttributes={
                'AWS.SNS.SMS.SenderID': {
                    'DataType': 'String',
                    'StringValue': sender,
                },
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': self.smstype,
                }
            }
        )
        app_log.info('SMS sent. SNS MessageId: %s', result['MessageId'])
        return result


class Twilio(Notifier):
    def __init__(self, account_sid, auth_token, **kwargs):
        raise NotImplementedError()
