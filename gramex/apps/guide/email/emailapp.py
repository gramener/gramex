import os
import gramex


def sendmail(handler):
    mailer = gramex.service.email[handler.get_argument('from')]
    folder = os.path.dirname(os.path.abspath(__file__))
    gramex.service.threadpool.submit(
        mailer.mail,
        to=handler.get_argument('to'),
        subject=handler.get_argument('subject', 'Gramex guide test'),
        html='<p>This is a <strong>test email</strong> from ' +
             '<a href="https://learn.gramener.com/guide/email/mail">Gramex</a></p>' +
             '<p><img src="cid:kitten"></p>',
        body='This is a plain text email from Gramex for non-HTML browsers',
        attachments=[os.path.join(folder, 'README.md')],
        images={'kitten': os.path.join(folder, 'kitten.jpg')},
    )
    return 'Mail is being sent. <a href=".">Back to email app</a>'
