title: Send email

The `email` service creates a service that can send email via SMTP. Here is a
sample configuration for GMail:

    :::yaml
    email:
        gramex-guide-gmail:
            type: gmail                     # Type of email used is GMail
            email: gramex.guide@gmail.com   # Generic email ID used to test e-mails
            password: tlpmupxnhucitpte      # App-specific password created for Gramex guide

In the `type:` section of `gramex.yaml` email configuration, the following types are supported:

- `gmail`: Google Mail. To securely send apps, enable
  [2-step verification](https://support.google.com/accounts/answer/185839) and use
  [app-specific password](https://support.google.com/accounts/answer/185833).
  Also see this [troubleshooting guide](https://support.google.com/mail/answer/78754).
- `yahoo`: Yahoo Mail
- `live`: Microsoft live mail
- `mandrill`: [Mandrill](https://mandrill.zendesk.com/) email

This creates an `SMTPMailer` instance that can be used as follows:

    :::python
    import gramex
    mailer = gramex.service.email['gramex-guide-gmail']
    result = mailer.mail(
        to='person@example.com',
        subject='Subject',
        html='<strong>This is bold text</strong> and <em>this is in italics</em>.'
        body='This plain text is shown if the client cannot render HTML',
        attachments=['1.pdf', '2.txt'])

See the source in the example below to understand how to use it.

<div class="example">
  <a class="example-demo" href="mail">Try a sample email</a>
  <a class="example-src" href="http://code.gramener.com/s.anand/gramex/tree/master/gramex/apps/guide/email/emailapp.py">Source</a>
</div>

## HTML email

Emails can have HTML content, text content, or both. HTML-friendly browsers like
Outlook, GMail, etc display HTML content where available, and fall back to the
text content.

The `html=` argument provides the HTML content. The `body=` argument provides the
text content.

Writing HTML for email is **quote different** than for browsers. Here are some
guides to read:

- [ActiveCampaign: HTML Email Design Guide](http://www.activecampaign.com/email-design-guide/)
- [MailChimp: Email design reference](https://templates.mailchimp.com/getting-started/html-email-basics/)
- [CampaignMonitor: Coding your emails](https://www.campaignmonitor.com/dev-resources/guides/coding/)

## Email attachments

Attachments can be specified as filenames or as a dictionary with the `body` and
`content_type` or `filename` keys. For example:

      attachments=['file.pdf']
      attachments=[{'filename': 'file.pdf', 'body': open('file.pdf', 'rb').read()}]
      attachments=[{'content_type': 'application/pdf', 'body': open('file.pdf', 'rb').read()}]

The attachment `dict` format is consistent with the `handler.request.files`
structure that holds uploaded files.
