---
title: Send email
prefix: Email
...

[TOC]

<iframe width="560" height="315" src="https://www.youtube.com/embed/GRTCgLsGVGE" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>

The `email` service creates a service that can send email via SMTP. Here is a
sample configuration for GMail:

```yaml
email:
    gramex-guide-gmail:
        type: gmail                     # Type of email used is GMail
        email: gramex.guide@gmail.com   # Generic email ID used to test e-mails
        password: tlpmupxnhucitpte      # App-specific password created for Gramex guide
```

In the `type:` section of `gramex.yaml` email configuration, the following types
are supported. You need to add your `email:` and `password:`.

- `gmail`: Google Mail. To securely send apps, enable
  [2-step verification](https://support.google.com/accounts/answer/185839) and use
  [app-specific password](https://support.google.com/accounts/answer/185833).
  Also see this [troubleshooting guide](https://support.google.com/mail/answer/78754).
- `yahoo`: Yahoo Mail
- `live`: Microsoft live mail
- `mandrill`: [Mandrill](https://mandrill.zendesk.com/) email
- `office365`: [Office 365](https://support.office.com/en-us/article/how-to-set-up-a-multifunction-device-or-application-to-send-email-using-office-365-69f58e99-c550-4274-ad18-c805d654b4c4)
- `outlook`: [Outlook.com](https://support.office.com/en-us/article/pop-imap-and-smtp-settings-for-outlook-com-d088b986-291d-42b8-9564-9c414e2aa040)
- `icloud`: [iCloud.com](https://support.apple.com/en-us/ht202304)

You can also connect to *any* SMTP or SMTPS mail server using `type: smtp` or
`type: smtps`. This includes:

- [Amazon SES via SMTP](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-email-smtp.html).
  This is not provided as a default type since there are
  [multiple endpoints](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/smtp-connect.html).
- [Microsoft Exchange](https://docs.microsoft.com/en-us/exchange/clients/pop3-and-imap4/configure-authenticated-smtp).
  The settings for this are based on the server

For example:

```yaml
email:
    amazon-ses:
        type: smtps
        host: email-smtp.eu-west-1.amazonaws.com    # AWS SES SMTP server for your region
        email: '***'                                # IAM access ID
        password: '***'                             # IAM password
    client-email:
        type: smtp              # Use type: smtps for SMTPS servers
        host: 10.20.30.40       # Host name or IP address of the SMTP server
        # Optional parameters
        email: user@domain.com  # Username or email to log into SMTP server
        password: '***'         # Password for SMTP server
        port: 587               # For non-standard SMTP port. Default: SMTPS=587, SMTP=25
```

## Send email

This creates an `SMTPMailer` instance that can be used as follows:

```python
from  gramex import service     # Available only if Gramex is running
mailer = service.email['gramex-guide-gmail']
# Or, to construct the SMTPMailer when using Gramex as a library, use:
# from gramex.services import SMTPMailer
# mailer = SMTPMailer(type='gmail', email='gramex.guide@gmail.com', password='...')
mailer.mail(
    to='person@example.com',
    subject='Subject',
    html='<strong>Bold text</strong>. <img src="cid:logo">'
    body='This plain text is shown if the client cannot render HTML',
    attachments=['1.pdf', '2.txt'],
    images={'logo': '/path/to/logo.png'})
```

The `mail()` method accepts the following arguments:

- `to`: a string with comma-separated emails, or a list of strings with emails
- `subject`: email subject
- `body`: plain text email content
- `html` HTML content of the email. If both `html` and `body` are specified, the
  email contains both parts, with HTML taking preference.
- `attachments`: array of absolute file paths
- `images` is a dict of `{key: path}`. `path` is the absolute path to an image.
  `key` may be anything. Include `<img src="cid:key">` in `html` to display it

You can also pass any standard email header. Use small letters, replacing `-`
with `_`. Here are some commonly used ones:

- `sender`: email id of sender. Defaults to the email ID of the account you've
  logged into. The `From:` field is also set to this unless you explicitly
  specify a different value.
- `cc`, `bcc`: a string with comma-separated emails, or a list of strings with emails
- `reply_to`: email ID that appears when the recipient replies
- `on_behalf_of`: email ID on behalf of whom you are sending this email

See the source in the example below to understand how to use it.

<div class="example">
  <a class="example-demo" href="mail">Try a sample email</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/email/emailapp.py">Source</a>
</div>

## HTML email

Emails can have HTML content, text content, or both. HTML-friendly browsers like
Outlook, GMail, etc display HTML content where available, and fall back to the
text content.

The `html=` argument provides the HTML content. The `body=` argument provides the
text content.

Writing HTML for email is **quite different** than for browsers. Here are some
guides to read:

- [ActiveCampaign: HTML Email Design Guide](http://www.activecampaign.com/email-design-guide/)
- [MailChimp: Email design reference](https://templates.mailchimp.com/getting-started/html-email-basics/)
- [CampaignMonitor: Coding your emails](https://www.campaignmonitor.com/dev-resources/guides/coding/)

## Email attachments

Attachments can be specified as filenames or as a dictionary with the `body` and
`content_type` or `filename` keys. For example:

```python
      attachments=['file.pdf']
      attachments=[{'filename': 'file.pdf', 'body': open('file.pdf', 'rb').read()}]
      attachments=[{'content_type': 'application/pdf', 'body': open('file.pdf', 'rb').read()}]
```

The attachment `dict` format is consistent with the `handler.request.files`
structure that holds uploaded files.

## Command-line emails

Gramex can be used as a standalone library to send emails as well. Here is a
sample Python application:

```python
from gramex.services import SMTPMailer

mailer = SMTPMailer(
    type='gmail',
    email='gramex.guide@gmail.com',       # Replace with your email ID
    password='tlpmupxnhucitpte',          # Replace with your passsword
)
mailer.mail(
    to='person@example.com',
    subject='Subject',
    html='<strong>This is bold text</strong> and <em>this is in italics</em>.'
    body='This plain text is shown if the client cannot render HTML',
    attachments=['1.pdf', '2.txt'])
```

The same parameters used in the `gramex.yaml` file may be used here.

## Automated email alerts

Combined with [schedule](../scheduler/), you can automate email alerts. For
example, this configuration sets up a schedule every weekday at 8am, and an email
service.

```yaml
schedule:
  email-alert:
    function: project.email_alert()     # Run this function
    hours: 8                            # at 8am on the system
    weekdays: mon,tue,wed,thu,fri       # every weekday

email:
  email-alert:                          # Define the email service to use
    type: smtp                          # Connect via SMTP
    host: mailserver.example.org        # to the mail server
    email: user@example.org             # with a login ID
    password: $MAIL_PASSWORD            # password stored in environment variable MAIL_PASSWORD
```

The `project.email_alert()` method can use this service to check if there are any
unusual events, and send a templatized email if so. Here is a sample workflow for
this:

```python
def email_alert():
    data = gramex.cache.open(data_file, 'xlsx')                   # Open the data source
    analysis = find_unusual_events(data)                          # Apply some analysis
    if 'unusual' in analysis:                                     # If something is unusual
        tmpl = gramex.cache.open(template_file, 'template')       #   open a template
        service.email['email-alert'].mail(                        #   and send the email
            to='recipients@example.org',                          #   to the recipients
            subject='Alert: {unusual}'.format(**analysis),        #   with a clear subject
            html=tmpl.generate(data=data, analysis=analysis),     #   and render the template.
            attachments=[data_file],                              #   Maybe attach the data
        )
```

## Test email service

To test an email service without sending an email, add `stub: log` to the
configuration. For example:

```yaml
email:
    email-test:
        type: gmail
        email: gramex.guide@gmail.com
        password: tlpmupxnhucitpte
        stub: log           # Don't send emails. Just print them to the console
```

When an email is sent via the `email-test` service above, it will not actually
be sent. The email contents will be printed on the console.
