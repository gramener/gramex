---
title: Smart alerts
prefix: Alerts
---

[TOC]

<iframe width="560" height="315" src="https://www.youtube.com/embed/RA5bxvsm8a0" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>

## Alert setup

The `alert` service sends reports via email based on conditions.

First, set up an [email service](../email/). Here is a sample:

```yaml
email:
  gramex-guide-gmail:
    type: gmail                     # Type of email used is GMail
    email: gramex.guide@gmail.com   # Generic email ID used to test e-mails
    password: tlpmupxnhucitpte      # App-specific password created for Gramex guide
```

## Alert examples

### Send a scheduled email

Email scheduling uses the same keys as [scheduler](../scheduler/): `minutes`,
`hours`, `dates`, `weekdays`, `months` and `years`.

```yaml
alert:
  alert-schedule:
    days: '*'                     # Send email every day
    hours: '6, 12'                # at 6am and 12noon
    minutes: 0                    # at the 0th minute, i.e. 6:00am and 12:00pm
    utc: true                     # GMT (or UTC). Set false for local server time
    to: admin@example.org
    subject: Scheduled alert
    body: This email will be scheduled and sent as long as Gramex is running.
```

To send an email on startup, use `startup:` instead of `days:`, `hours:`, etc.
This sends an email every time Gramex starts.

You can use `startup:` **and** the schedule (`days:`, `hours:`, etc) together.
This will send an email on startup and at the specified schedule.

(Before Gramex 1.31, emails without a schedule were sent out once automatically.
This led to work-in-progress messages being emailed. From Gramex 1.31, all mails
require a `startup:` or a [schedule](#send-a-scheduled-email).)

### Avoid re-sending emails

`condition: once(..)` ensures that an alert campaign is sent out only once.
For example:

```yaml
alert:
  alert-condition-once:
    condition: once(r'$YAMLPATH', 'unique-key')
    ...
```

... will send out the email only once, unless the `'unique-key'` is changed.

### Send as a different user

`from:` lets you choose a different user to send as. **Note:** this won't work
on GMail unless you enable
[Send emails from a different address or alias](https://support.google.com/mail/answer/22370?hl=en)

```yaml
alert:
  alert-as-user:
    to: "User name <admin@example.org>"
    from: "Sender name <sender@example.org>"
    subject: Alert from Gramex
    body: This email is sent as if from sender@example.org
```

### Reply to different user

`reply_to:` picks a different user to send a reply to. When the user gets the
email, it is from the `from:` ID or the email service account. But when the
user replies, the reply is sent to the `reply_to:` address. For example:

```yaml
alert:
  alert-as-user:
    to: "User name <admin@example.org>"
    reply_to: "Reply Person <reply@example.org>"
    subject: Alert from Gramex
    body: Replies to this email will be addressed to reply@example.org
```

You may also use the `on_behalf_of:` header to indicate that you're sending the
alert on behalf of a different user.

### Email multiple people

The `to:`, `cc:` and `bcc:` fields accept a list or comma-separated email IDs.
[Preview](preview/?alert=alert-email).

```yaml
alert:
  alert-email:
    service: email-service
    to:
      - Admin <admin@example.org>
      - "Admin 2 <admin2@example.org>"
    cc: cc@example.org, cc2@example.org
    bcc: cc@example.org, cc2@example.org
    subject: Gramex started
    body: |
      This email is sent to multiple people. The to:, cc:, bcc: fields
      accept a list or a comma-separated string of email IDs.
```

### Send HTML email

`html:` specifies the HTML content to be sent. `body:` can be used along with
HTML. Email clients choose which content to render based on their capability.
[Preview](preview/?alert=alert-html).

```yaml
alert:
  alert-html:
    to: admin@example.org
    subject: HTML email
    body: This content will only be displayed on devices that cannot render HTML email. That's rare.
    html: <p>This content will be shown in <em>HTML</em> on <strong>supported devices</strong>.
```

`markdown:` can be used to specify the HTML content as Markdown instead of
`html` (and overrides it). [Preview](preview/?alert=alert-markdown).

```yaml
alert:
  alert-markdown:
    to: admin@example.org
    subject: Markdown email
    body: This content will only be displayed on devices that cannot render HTML email. That's rare.
    markdown: |
      This is Markdown content.
      Markup like *emphasis* and **strong** are supported.
```

### Place body and HTML in a file

`bodyfile:`, `htmlfile:` and `markdownfile:` load content from files instead of
directly typing into the `body`, `html` or `markdown:` keys.
[Preview](preview/?alert=alert-content-file).

```yaml
alert:
  alert-content-file:
    to: admin@example.org
    subject: HTML email from file
    bodyfile: $YAMLPATH/email.txt       # Use email.txt in current directory
    htmlfile: $YAMLPATH/email.html      # Use email.html in current directory
    markdownfile: $YAMLPATH/email.md    # Use email.md in current directory
```

### Send inline images

`images:` specifies one or more `<key>: <url>` entries. Each `<key>` can be
embedded into the email as an image using `<img src="cid:<key>">`. The `<url>`
can be a file path or a URL. [Preview](preview/?alert=alert-images).

```yaml
alert:
  alert-images:
    to: admin@example.org
    subject: Inline images
    markdown: |
      <p>This email has 2 inline images.</p>
      <p><img src="cid:img1"></p>
      <p><img src="cid:img2"></p>
    images:
      img1: $YAMLPATH/../uicomponents/bg-small.png
      img2: https://en.wikipedia.org/static/images/wikimedia-button.png
```

### Send attachments

`attachments:` specifies one or more `<key>: <url>` entries. Each entry is added
to the email as an attachment. The `<url>` can be a file path or a URL.
[Preview](preview/?alert=alert-attachments).

```yaml
alert:
  alert-attachments:
    to: admin@example.org
    subject: Email with attachments
    html: This email contains attachments.
    attachments:
        - $YAMLPATH/doc1.docx
        - https://example.org/sample.pptx
```

### Alert templates

The `to`, `cc`, `bcc`, `from`, `subject`, `body`, `html`, `bodyfile`, `htmlfile`
fields can all use Tornado templates to dynamically generate values.

```yaml
alert:
  alert-templates:
    to: '{{ "admin@example.org" }}'
    subject: Template email
    html: |
      {% import sys %}
      <p>This email was sent from {{ sys.platform }}.</p>
      <p><img src="cid:img"></p>
      <p>{% raw open(r'$YAMLPATH/email.html').read() %}</p>
    images:
      img: '{% import os %}{{ os.path.join(r"$YAMLPATH", "../uicomponents/bg-small.png") }}'
    attachments:
      - '{% import os %}{{ os.path.join(r"$YAMLPATH", "doc1.docx") }}'
```

Tornado templates escape all HTML content. To pass the HTML content raw,
use `{% raw expression %}` instead of `{{ expression }}`.

The templates can use these variables:

- `config`: the alert configuration as an AttrDict. For example,
  `config.subject` is the subject configuration
- Each dataset passed to the alert is available as a variable:
    - If a single dataset is passed, `data` holds the dataset
    - If multiple datasets are passed as a dict of `{<key>: ...}`,
    - then the variable `<key>` holds the respective dataset
- If `each:` is used, then the following variables are also available:
    - `row`: the data for each entry that `each:` loops through
    - `index`: the key or index number of each entry
- `args`: If you run `alert.run(args=...)` via [alert API](#alert-api)
  it holds whatever value was passed. It defaults to an empty dict `{}`.

### Email dashboards

To send a dashboard as an inline-image or an attachment, set up a
CaptureHandler, then use its URL as the image and/or attachment.

```yaml
alert:
  alert-capture:
    to: admin@example.org
    subject: Dashboard attachment
    html:
      <h1>Sample dashboard</p>
      <p><img src="cid:img"></p>
    images:
      img: http://server/capturehandler/?url=http://server/dashboard&ext=png
    attachments:
      - http://server/capturehandler/?url=http://server/dashboard&ext=pdf
    # Optional: to capture the dashboard as a specific user, add this user section
    # user:
    #   id: user@example.org
    #   email: {{ config['to'] }}       # User object values can be templates
    #   role: manager
```

**Note**: If the server that sends the alert is the same as the the server that
runs CaptureHandler, you must specify `thread: true`.

The `user:` section sends an [X-Gramex-User](../auth/#encrypted-user) header to
take a screenshot of a dashboard as the user would have seen it. Specify the
entire `user` object here. Values in `user:` can be [templates](#alert-templates).


### Dynamic emails from data

`data:` specifies one or more datasets. You can use these in templates to create
dynamic content based on data. The `data:` can be:

- a string [FormHandler URL](../formhandler/).
  `data: file.xlsx` loads data from a CSV or Excel file as a DataFrame
- a dict [FormHandler definition](../formhandler/).
  `data: {url: ..., table: ...}` loads data from a SQLAlchemy URL and table
- a list of raw data.
  `data: [... list of objects ...]` defines data as a list of objects in the YAML file

The data is available to templates in a variable called `data`.

```yaml
alert:
  alert-templates:
    data:
      - {month: Jan, sales: 100}
      - {month: Feb, sales: 110}
      - {month: Mar, sales:  90}
    to: admin@example.org
    subject: 'Email generated from data'
    html: 'Total sales was {{ sum(row["sales"] for row in data) }}'
```

Multiple datasets can be defined as a dict containing different keys. Here is an
example that covers all variations:

```yaml
alert:
  data:
    plainlist:
      - {month: Jan, sales: 100}
      - {month: Feb, sales: 110}
      - {month: Mar, sales:  90}
    sales: $YAMLPATH/sales.xlsx
    employees:
      url: mysql://root@localhost/hr
      table: employee
```

This data can be used directly in templates as variables named `plainlist`,
`sales` and `employee`.

### Mail merge: change content by user

`each:` specifies a dataset to iterate over. Each row becomes a separate email.

`condition:` is a Python expression that filters the data and returns the final
rows to send as email. If the result is `False`, `[]`, `{}` or any false-y
value, the alert will exit.

Here is an example of a birthday alert email sent every day. (This assumes that
`birthday.csv` has a column called `birthday` which has a format like
`10-Aug-2018`.)

```yaml
alert:
  alert-birthday:
    data: $YAMLPATH/birthday.csv
    condition: data[data['birthday'] == datetime.datetime.today().strftime('%d-%b-%Y')]
    each: data          # Loop through each row, i.e. person whose birthday is today
    to: {{ row['email'] }}                      # Use the "email" column for the person's email ID
    subject: Happy birthday {{ row['name'] }}   # Use the "name" column for the person's name
    days: '*'           # Schedule birthday mail every day
    hours: 6            # at 6:00am local time
    minutes: 0
```

### Send alerts on condition

Send an alert to each sales person, but only if they did not meet the target.

```yaml
alert:
  alert-sales-target:
    data:
      sales:
        url: mysql+pymysql://user:password@server/database
        query: 'SELECT * FROM sales'
    condition: sales[sales['target'] < sales['value']]
    each: sales
    to: {{ row['email'] }}
    cc: salesmanager@example.org
    subject: Sales target deficit of {{ row['target'] - row['value'] }}
```

### Send notification on alert

To send a notification alert *after* your alert(s) are done, use `notify:`.
`notify:`  is a list of alerts to trigger after this alert runs.

The notification alerts get an `args` data variable. This holds the history of
notification successes and failures. For example:

```yaml
alert:
  alert-mail:
    to: 'user@example.org'
    data: ...
    each: ...
    subject: ...
    notify: [alert-notify, alert-success, alert-failure]
  alert-notify:                   # Send notification after alert
    to: 'admin@example.org'
    subject: 'Sent {{ len(args["done"]) }} alerts, failed {{ len(args["fail"]) }} alerts'
  alert-failure:
    condition: args["fail"]       # Send notification only if there's a failure
    to: 'admin@example.org'
    subject: 'Failed on {{ len(args["fail"]) }} alerts. Sent {{ len(args["done"]) }}'
  alert-success:
    condition: not args["fail"]   # Send notification only if all alerts were successful
    to: 'admin@example.org'
    subject: 'Sent all {{ len(args["done"]) }} alerts'
```

- `args['done']` is a list of dicts for sent emails. Each dict has keys:
    - `mail`: the email object that was sent. It has the following keys:
        - `to`: sender
        - `subject`: email subject
        - `html`: html content
        - `body`: body plain text content
        - `attachments`: list of attachments
        - `images`: dict of {image_name: path_to_image}
        - other email headers such as `cc`, `bcc`, `reply_to`, etc
    - `index`: the index of the email sent. If `each:` is used on a DataFrame or
      dict, this is the key
    - `row`: the data used in the email to be sent. If `each:` is used on a
      DataFrame or dict, this is the value
- `args['fail]` is a list of dicts for failed emails. This is identical to
  `args['done']` but has an additional key:
    - `error`: the Exception object that caused the failure


### Use multiple datasets

TODO

### Use multiple services

If you have more than one `email:` service set up, you can specific which email
service to use using `service: name-of-email-service`.

## Alert preview

You can preview and run alerts manually using the
[Admin Alert](../admin/#admin-alerts) component at
[/admin/alert](../admin/admin/alert).

**Note**: Before Gramex 1.54, there was a mail app that you could import. That is now deprecated.

## Alert logs

All emails sent via alerts are logged at `$GRAMEXDATA/logs/alert.csv` and is
archived weekly by default. It stores these columns:

- datetime: when the email was sent, as `YYYY-mm-dd %H:%M:%SZ`
- alert: name of the alert that triggered the email
- service: name of the service used to send the email
- from: sender email ID
- to: comma-separated list
- cc: comma-separated list
- bcc: comma-separated list
- subject: email subject
- attachments (comma-separated list of filenames)


## Alert configuration

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
  - `startup`: set this to `true` to run the alert at startup. Set to `*` to run
    on startup *and* every time the configuration changes. Default: `false`
  - `thread`: set this to `true` to run in a separate thread. Default: `false`
- email configuration determines whom to send the alert to.
  - `service`: name of the [email service](../email/) to use for sending emails.
    Required, but if only one [email service](../email/) is defined, it is used.
  - `to`: a string with comma-separated emails. Optional
  - `cc`: like `to:` but specifies the cc: addresses. Optional
  - `bcc`: like `to:` but specifies the bcc: addresses. Optional
  - `from`: email ID of sender. This overrides the `service:` from ID if possible. Optional
- content configuration determines what to send. All values are strings interpolated as Tornado templates
  - `subject`: subject template for the email. Optional
  - `body`: string for email text template. Optional
  - `html`: string for email html template. Optional
  - `bodyfile`: file for email body template. Optional
  - `htmlfile`: file for email html template. Optional
  - `attachments`: attachments as a list of files. Optional
  - `images`: inline image attachments as a dictionary of key:path. These
    can be linked from HTML emails using `<img src="cid:key">`. Optional
  - For all the above, the variables available in the Tornado templates are:
    - All dataset keys loaded from the `data:` section are available as variables.
      If `data:` directly specifies a variable, it is stored in a `data` variable
    - `config` holds the alert configuration -- e.g. `config.to` is the recipient
    - `row` and `index` contain the row values and index if `each:` is used
- data configuration uses data to drive the content and triggers.
  - `data`: Optional data file or dict of datasets. All keys are available as
    variables in the content templates and to `condition`. Optional. Examples:
      - `data: {key: [...]}` -- loads data in-place
      - `data: {key: {url: file}}` -- loads from a file
      - `data: {key: {url: sqlalchemy-url, table: table}}` -- loads from a database
      - `data: file` -- same as `data: {data: {url: file}}`
      - `data: {key: file}` -- same as `data: {key: {url: file}}`
      - `data: [...]` -- same as `data: {data: [...]}`
  - `each`: dataset name. Optional. It sends an email for each element of the
    dataset. This adds 2 variables: `index` and `row`. If the dataset is a:
    -  dict: `index` and `row` are the key and value
    -  list: `index` and `row` are the index and value
    -  DataFrame: `index` and `row` are the row index and DataFrame row
  - `condition`: an optional Python expression that determines whether to run the
    alert. All `data:` keys are available to the expression. This may return a:
    - False-y value or empty DataFrame: to prevent running the alert. For example,
      the `once()` transform can be used. e.g. `once('unique-key')` runs the alert
      only once for every unique value of the arguments.
    - dict: to update the loaded `data:` variables
    - new DataFrame: to replace `data['data']`
- subscriptions configuration allows users to subscribe to and unsubscribe from
  these alerts, and specify how often they should get emails (TODO)

## Alert API

To run an existing alert, run `gramex.service.alert['your-alert-name'].run()`.
Replace `'your-alert-name'` with the name (key) of the alert you created.
For example:

```python
import gramex

def functionhandler(handler):
    # This triggers the alert called my-alert-name
    gramex.service.alert['my-alert-name'].run()
```

You can call `.run(args=...)` to pass an optional `args` variable to the
templates. This can be used in the [alert templates](#alert-templates) as
a variable `args`. For example, this alert:

```yaml
alert:
  my-alert-name:
    to: '{{ args.get('to', 'default@example.org') }}'
```

... will email `default@example.org`. But when you run
`gramex.service.alert(...).run(args={'to': 'hi@example.org'})`, it will email
`hi@example.org`.


To **create** an alert programmatically use
`gramex.services.create_alert(config)`.
This returns a function that sends an alert based on the configuration.

```python
import yaml
import gramex.services

conf = {
  'to': 'admin@example.org',
  'subject': 'Alert from Gramex',
  'body': 'This was sent from an API',
}

alert = gramex.services.create_alert('api-alert', conf)
kwargs = alert()
```

The returned `kwargs` are the computed email contents.


## Alert command line

Alerts can be used from the command line by running `gramex mail`.

- `gramex mail` displays help about usage
- `gramex mail <key>` sends mail named `<key>`
- `gramex mail --list` lists all keys in config file
- `gramex mail --init` initializes config file

To set it up:

1. Run `gramex mail --init`. This prints the location of the config file
2. Edit the config file and set up the [email section](../email/):
3. Set `type:` to the email service type (e.g. `gmail`, `smtp`, etc.)
4. `email:`: is `$GRAMEXMAILUSER` and `password:` is `$GRAMEXMAILPASSWORD`.
   Set the environment variables `GRAMEXMAILUSER` and `GRAMEXMAILPASSWORD`
   and these will be used.
5. Note: If you're using two-factor authentication on Google, create an
   [app-specific password](https://security.google.com/settings/security/apppasswords)

To create an email, edit the config file and [add an alert](#alert-examples)
like in a `gramex.yaml` file.

To send the email, run `gramex mail <key>` where `<key>` is the alert key.
For example, with this configuration:

```yaml
alert:
  birthday-greeting:
    to: john@example.org
    subject: Happy birthday
    body: Happy birthday John!
```

... the command `gramex mail birthday-greeting` will send the email.
