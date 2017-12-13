title: Smart alerts

[TOC]

The `alert` service sends reports via email based on conditions. Here is a
sample configuration to send an email:

    :::yaml
    alert:
        simple-alert:
            days: '*'                         # Run every day
            hours: 8, 16                      # at 8am and 4pm
            minutes: 0
            service: gramex-email-guide       # Send an email via this email-service
            to: 'user@example.com'            # to this list of users
            subject: Smart Alert Sample       # with the specified subject
            template: Hello from Smart Alert  # and content

The alert service takes four kinds of parameters:

- schedule configuration determines when the schedule is run. It uses the same
  keys as [scheduler timing](../scheduler/#scheduler-timing). (If no schedule is
  specified, the alert will not run.)
  - `years`: which year(s) to run on, e.g. "2018, 2019". Default: `*`
  - `months`: which month(s) to run on, e.g. "Jan-Mar,May". Default: `*`
  - `weekdays`: which weekdays(s) to run on, e.g. "Mon-Wed,Sat". Default: `*`
  - `dates`: which date(s) to run on, e.g. "10, 20, 30". Default: `*`
  - `hours`: which hour(s) to run at, e.g. "*/3" for every 3rd hour. Default: `*`
  - `minutes`: which minute(s) to run at, e.g. "*" for every minute. Default: `*`
  - `startup`: set this to `true` to run the alert at startup. Default: `false`
  - `thread`: set this to `true` to run in a separate thread. Default: `false`
- email configuration determines whom to send the alert to.
  - `service`: name of the [email service](../email/) to use for sending emails. Required
  - `to`: a string with comma-separated emails. Optional
  - `cc`: like `to:` but specifies the cc: addresses. Optional
  - `bcc`: like `to:` but specifies the bcc: addresses. Optional
  - `from`: email ID of sender. This overrides the `service:` from ID if possible. Optional
- content configuration determines what to send. All values are strings interpolated as Tornado templates.
  - `subject`: subject template for the email. Optional
  - `body`: string for email text template. Optional
  - `html`: string for email html template. Optional
  - `bodyfile`: file for email body template. Optional
  - `htmlfile`: file for email html template. Optional
  - `attachments`: attachments as a list of files. Optional
  - `images`: inline image attachments as a dictionary of key:path. These
    can be linked from HTML emails using `<img src="cid:key">`. Optional
  - `capture`: screenshot attachments (TODO)
- data configuration uses data to drive the content and triggers.
  - `data`: data file or dict of datasets. A dataset can be `key: {url: file}` or
    as `key: {url: sqlalchemy-url, table: table}`. All keys are available as
    variables in the content templates and to `condition`. If `data: file` is
    used, the key name defaults to `data`. Optional
  - `each`: dataset name. Optional. It sends an email for each element of the
    dataset. This adds 2 variables: `index` and `row`. If the dataset is a:
        - dict: `index` and `row` are the key and value
        - list: `index` and `row` are the index and value
        - DataFrame: `index` and `row` are the row index and DataFrame row
  - `condition`: an optional Python expression that determines whether to run the
    alert. All `data:` keys are available to the expression. Returning a
        - False-y value or empty DataFrame prevents running the alert
        - dict updates the loaded `data:` variables
        - DataFrame replaces the variable named `data`
- subscriptions configuration allows users to subscribe to and unsubscribe from
  these alerts, and specify how often they should get emails (TODO)

## Scheduler examples

Send an email when Gramex starts up

    :::yaml
    alert-startup:
      startup: true
      service: email-service
      to: admin@example.org
      subject: Gramex started

Send an email every day at 6am and 12noon

    :::yaml
    alert-schedule:
      days: '*'
      hours: '6, 12'
      minutes: 0
      service: email-service
      to: admin@example.org
      subject: Scheduled alert

Send an email to multiple people

    :::yaml
    alert-email:
      startup: true
      service: email-service
      to: admin@example.org, admin2@example.org
      cc: cc@example.org, cc2@example.org
      bcc: cc@example.org, cc2@example.org
      subject: Gramex started

Send a HTML + text email using templates:

    :::yaml
    alert-content:
      startup: true
      service: email-service
      to: admin@example.org
      subject: Gramex started
      body: This is a template running on {{ sys.platform }}
      html: This is a <strong>template</strong> on <em>{{ sys.platform }}</em>

Send a HTML + text email using template files:

    :::yaml
    alert-content-file:
      startup: true
      service: email-service
      to: admin@example.org
      subject: Gramex started
      bodyfile: $YAMLPATH/{{ 'email' + '.txt' }}    # Contents are treated as templates too
      htmlfile: $YAMLPATH/{{ 'email' + '.html' }}   # Contents are treated as templates too

Send HTML email with inline image and attachments

    :::yaml
    alert-attachments:
      startup: true
      service: email-service
      to: admin@example.org
      subject: From {{ sys.platform }}
      html: <p>Hello user</p><p><img src="cid:img1"></p><p><img src="cid:img2"></p>
      images:
         img1: $YAMLPATH/img1.jpg
         img2: $YAMLPATH/{{ 'img2' + '.jpg' }}
      attachments:
         - $YAMLPATH/doc1.docx
         - $YAMLPATH/{{ 'ppt1' + '.pptx' }}

Send birthday alert emails every day

    :::yaml
    alert-birthday:
      data: $YAMLPATH/birthday.csv
      condition: data[data['date'] == datetime.datetime.today()]
      each: data
      service: email-service
      to: {{ row['email'] }}
      subject: Happy birthday {{ row['name'] }}

Send monthly alert if sales is below target

    :::yaml
    alert-sales-target:
      months: '*'
      data:
        sales:
          url: mysql+pymysql://user:password@server/database
          query: 'SELECT * FROM sales'
      condition: sales[sales['target'] < sales['value']]
      each: sales
      service: email-service
      to: {{ row['email'] }}
      cc: salesmanager@example.org
      subject: Sales target deficit of {{ row['target'] - row['value'] }}
      html: $YAMLPATH/salestarget.html
