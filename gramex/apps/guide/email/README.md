title: Send email

The `email` service creates a service that can send email via SMTP. Here is a
sample configuration for GMail:

    :::yaml
    email:
        gramex-guide-gmail:
            type: gmail                     # Type of email used is GMail
            email: gramex.guide@gmail.com   # Generic email ID used to test e-mails
            password: tlpmupxnhucitpte      # App-specific password created for Gramex guide

This creates an `SMTPMailer` instance that can be used as follows:

    :::python
    import gramex
    mailer = gramex.service.email['gramex-guide-gmail']
    result = mailer.mail(
        to='person@example.com',
        subject='Subject',
        body='Email text')

<div class="example">
  <a class="example-demo" href="mail">Try a sample email</a>
  <a class="example-src" href="http://code.gramener.com/s.anand/gramex/tree/master/gramex/apps/guide/email/emailapp.py">Source</a>
</div>

You can use the following types for email as of now:

- `gmail`: Google Mail. To securely send apps, enable
  [2-step verification](https://support.google.com/accounts/answer/185839) and use
  [app-specific password](https://support.google.com/accounts/answer/185833).
  Also see this [troubleshooting guide](https://support.google.com/mail/answer/78754).
- `yahoo`: Yahoo Mail
- `live`: Microsoft live mail
- `mandrill`: [Mandrill](https://mandrill.zendesk.com/) email
