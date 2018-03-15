---
title: Send SMS
prefix: SMS
...

[TOC]

**v1.30**. The `sms` service creates a service that can send mobile messages via
APIs. Here is a sample config for [Amazon SNS](https://aws.amazon.com/sns/):

```yaml
sms:
  amazonsns:
    type: amazonsns
    aws_access_key_id: ...
    aws_secret_access_key: ...
    region_name: ap-southeast-1
    smstype: Transactional
```

Only `type: amazonsns` is supported. [Twilio SMS](https://www.twilio.com/sms)
is on the roadmap.

To set up SNS:

- [Create a new IAM user](https://console.aws.amazon.com/iam/home/?#users)
  - with **Access type** as **Programmatic access**.
  - to a new group with `AmazonSNSFullAccess` policy enabled
- [Create an access key](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_CreateAccessKey)
  and copy the **Access key id** and **Secret access key**.
- Add the keys to `gramex.yaml`

The `smstype` parameter for Amazon SNS can be either

- `Transactional`: for operational messages
- `Promotional`: for sales / marketing messages. These may not be delivered
  to numbers in the [DNC registry][dnc], and may be rate-limited.

[dnc]: http://www.nccptrai.gov.in/nccpregistry/search.misc


## Send SMS

This creates a `Notifier` instance that can be used as follows:

```python
import gramex
notifier = gramex.service.sms['amazon']
# Or, to construct the Notifier when using Gramex as a library, use:
# from gramex.services import AmazonSNS
# notifier = AmazonSNS(aws_access_key_id, aws_access_secret_key, region_name)
notifier.send(
    to='+919741552552',         # International mobile number
    subject='Message to send',  # Text message to send
    sender='Gramex',            # Optional sender identifier
)
```

Messages are typically delivered instantly, but may be delayed by up to 2 minutes.

Here is a sample form to send messages:

<form action="send" method="POST">
  <p><input required type="tel" name="to" placeholder="Send to +91 ..."></p>
  <p><input required type="text" name="subject" placeholder="Subject"></p>
  <p><input required type="text" name="sender" placeholder="Sender"></p>
  <p><button type="submit">Send SMS</button></p>
</form>

**Note**: Depending on the geography, the "Sender" field may not be sent. In
India, it is not. The sender is replaced with "HP-Notice" or similar messages.
In Singapore, the Sender field is used as-is.
