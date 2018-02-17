---
title: Automated email alerts in Gramex
prefix: Tip
...

Gramex's email and schedule capabilities can be combined to schedule automated email alerts.

For example, this configuration sets up a schedule every weekday at 8am, and an email
service.

    :::yaml
    schedule:
      email-alert:
        function: app.email_alert()    # Run this function
        hours: 8                       # at 8am on the system
        weekdays: mon,tue,wed,thu,fri  # every weekday

    email:
      email-alert:                      # Define the email service to use
        type: smtp                      # Connect via SMTP
        host: 'mailserver.example.org'    # to the mail server
        email: 'user@example.org'         # with a login ID
        password: $PASSWORD             # password stored in an environment variable

The 1app.email_alert()` method can use this service to check if there are any
unusual events, and send a templatized email if so. Here is a sample workflow for
this:

    :::python
    def email_alert():
        data = gramex.cache.open(data_file, 'xlsx')                   # Open the data source
        analysis = find_unusual_events(data)                          # Apply some analysis
        if 'unusual' in analysis:                                     # If something is unusual
            tmpl = gramex.cache.open(template_file, 'template')       #   open a template
            gramex.service.email['email-alert'].mail(                 #   and send the email
                to='recipients@example.org',                          #   to the recipients
                subject='Alert: {unusual}'.format(**analysis),        #   with a clear subject
                html=tmpl.generate(data=data, analysis=analysis),     #   and render the template.
                attachments=[data_file],                              #   Maybe attach the data
        )
