---
title: Send SMS
prefix: SMS
...

[TOC]

**v1.30**. The `sms` service creates a service that can send mobile messages via
APIs. Multiple SMS APIs are supported:

- [Amazon SNS](#amazon-sns) from v1.30
- [Exotel](#exotel) from v1.36

## Amazon SNS

Here is a sample config for [Amazon SNS](https://aws.amazon.com/sns/):

```yaml
sms:
  amazonsns:
    type: amazonsns
    aws_access_key_id: ...
    aws_secret_access_key: ...
    region_name: ap-southeast-1
    smstype: Transactional
```

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

Notes:

- Messages are typically delivered instantly, but may be delayed by up to 2 minutes.

[dnc]: http://www.nccptrai.gov.in/nccpregistry/search.misc


## Exotel

Here is a sample config for [Exotel](https://exotel.com/product-sms/):

```yaml
sms:
  exotel:
    type: exotel
    sid: ...
    token: ...
    priority: high      # can be high or normal. Defaults to high
```

To set up Exotel:

1. Create a developer account at <https://developer.exotel.com/>
1. Visit Settings > Sender ID. Click Change icon. Add a 6 character string.
   Await approval by the Exotel team.
1. Visit Settings > SMS Templates. Add a transactional template. For example:
   `OTP requested by %s with mobile %s.`. Request approval.
1. Visit Settings  > API Settings. Use the Exotel SID and Exotel Token in
   `gramex.yaml`.

Notes:

1. The mobile number can be in any format. `+91 9741 552 552`, `09741552552`, `9741-552-552` are the same.
1. Use ``%s`` for numbers as well as text, despite the Exotel documentation.
1. Do not end with a variable, e.g. ``mobile %s` is invalid. But ``mobile
    %s.`` with a period (.) at the end is valid.
1. Cost: Rs 0.15 per SMS

See the Exotel documentation at <https://developer.exotel.com/api/#send-sms>.


## Twilio

[Twilio SMS](https://www.twilio.com/sms) is on the roadmap.


## Send SMS

To send an SMS programmatically -- for example, inside a
[FunctionHandler](../functionhandler/) or in a [scheduler](../scheduler/):

```python
import gramex
notifier = gramex.service.sms['amazon']     # Available only if Gramex is running
# Or, to construct the Notifier when using Gramex as a library, use:
# from gramex.services import AmazonSNS
# notifier = AmazonSNS(aws_access_key_id, aws_access_secret_key, region_name)
result = notifier.send(
    to='+919741552552',         # International mobile number
    subject='Message to send',  # Text message to send
    sender='Gramex',            # Optional sender identifier
)
```

The `result` has the API response which contains additional information about
the SMS. To fetch its delivery status, use:

```python
status = notifier.status(result)    # Not available for Amazon SNS
```

This returns the API response for the delivery status.

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
