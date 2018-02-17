---
title: Send Emails from the command line
prefix: Tip
...

Gramex can be used to write standalone applications that send emails. You don't need to run Gramex. Just use it as a library.

Here's a code snippet that you can run to test sending emails (just change the `to=` email ID to your ID).

    :::python
    from gramex.services import SMTPMailer
    mailer = SMTPMailer(
        type='gmail',
        email='gramex.guide@gmail.com',   # Replace with your email ID
        password='tlpmupxnhucitpte',      # Replace with your passsword
    )
    mailer.mail(
        to='person@example.com',
        subject='Subject',
        html='<strong>This is bold text</strong> and <em>this is in italics</em>.'
        body='This plain text is shown if the client cannot render HTML',
        attachments=['1.pdf', '2.txt']
    )

More on the [Gramex guide on email](../email/).
