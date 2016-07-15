import gramex


def sendmail(handler):
    mailer = gramex.service.email[handler.get_argument('from')]
    gramex.service.threadpool.submit(mailer.mail,
        to=handler.get_argument('to'),
        subject=handler.get_argument('subject', 'Gramex guide test'),
        body='This is a test email from Gramex')
    return 'Mail is being sent. <a href=".">Back to auth</a>'
