---
title: Auth handlers log in users
prefix: Auth
...

Your session data is:
<iframe frameborder="0" src="session"></iframe>

[TOC]

# Sessions

Gramex identifies sessions through a cookie named `sid`, and stores information
against each session as a persistent key-value store. This is available as
`handler.session` in every handler. For example, here is the contents of your
[session](session) variable now:

<iframe frameborder="0" src="session"></iframe>

This has a `randkey` variable that was generated using the following code:

```python
def store_value(handler):
    handler.session.setdefault('randkey', random.randint(0, 1000))
    return json.dumps(handler.session)
```

The first time a user visits the [session](session) page, it generates the
`randkey`. The next time this is preserved.

The cookie is [HttpOnly](https://www.owasp.org/index.php/HttpOnly) - you cannot
access it via JavaScript. On HTTPS connections, it is also a marked as a
[Secure](https://www.owasp.org/index.php/SecureFlag) cookie - you cannot access
the same cookie via HTTP.

You can store any variable against a session. These are stored in the `sid`
secure cookie for a duration that's controlled by the `app.session.expiry`
configuration in `gramex.yaml`. Here is the default configuration:

```yaml
app:
    session:
        expiry: 31                      # Session cookies expiry in days
```

You can override session expiry duration with a `session_expiry: <days>` kwarg
under any auth handler. See [session expiry](#session-expiry).

The cookies are encrypted using the `app.settings.cookie_secret` key. Change
this to a random secret value, either via `gramex --settings.cookie_secret=...`
or in you `gramex.yaml`:

```yaml
app:
    settings:
        cookie_secret: ...
```

## Session data

Session data is stored in a session store that is configured as follows:

```yaml
app:
    session:
        type: json                      # Type of store to use: json, sqlite, memory
        path: $GRAMEXDATA/session.json  # Path to the store (ignored for type: memory)
        expiry: 31                      # Session cookies expiry in days
        flush: 5                        # Write store to disk periodically (in seconds)
        purge: 3600                     # Delete old sessions periodically (in seconds)
```

Sessions can be stored in one of these `type:`

| `type`    | Speed     | Persistent | Distributed |
|:---------:|:---------:|:----------:|:-----------:|
| `memory`  | faster    | no         | no          |
| `json`    | fast      | yes        | no          |
| `sqlite`  | slow      | yes        | yes         |

- Persistent means that it will be saved if Gramex restarts
- Distributed means multiple Gramex instances can use it at the same time.

The default is `type: json`. Stick to this. But if you have multiple Gramex
instances, use `type: sqlite` and change the `path:` to an SQLite file.

Here is an example of a session store that works across multiple Gramex instances.

```yaml
app:
    session:
        type: sqlite                    # Persistent multi-instance data store
        path: $GRAMEXDATA/session.db    # Path to the sqlite store
        expiry: 31                      # Session cookies expiry in days
        flush: 5                        # Clear expired sessions periodically (in seconds)
        purge: 3600                     # Delete old sessions periodically (in seconds)
```

Note: `type: hdf5` is deprecated from **v1.34**. It is very slow and not distributed.

You can access the session data directly from the session store file, or via
Gramex as follows:

```python
from gramex.handlers.basehandler import session_store_cache
# Loop through each session store -- there may be multiple stores
for store in session_store_cache.values():
    for session_id in store.store:
        print('Found session ID', session_id)
```

You can also access session data from inside a handler via:

```python
for session_id in handler._session_store.store:
    print('Found session ID', session_id)
```

# Authentication

Gramex allows users to log in using various single sign-on methods. The flow
is as follows:

1. Define a Gramex auth handler. This URL renders / redirects to a login page
2. When the user logs in, send the credentials to the auth handler
3. If credentials are valid, store the user details and redirect the user. Else
   show an error message.

After logging in, users are re-directed to the `?next=` URL. You can change this
using the [redirection configuration](../config/#redirection).

Every time the user logs in, the session ID is changed to prevent
[session fixation](https://www.owasp.org/index.php/Session_fixation).


## Simple auth

This configuration creates a [simple auth page](simple):

```yaml
url:
    login/simple:
        pattern: /$YAMLURL/simple   # Map this URL
        handler: SimpleAuth         # to the SimpleAuth handler
        kwargs:
            credentials:            # Specify the user IDs and passwords
                alpha: alpha        # User: alpha has password: alpha
                beta: beta          # Similarly for beta
                gamma:              # The user gamma is defined as a mapping
                    password: pwd   # One of the keys MUST be "password"
                    role: user      # Additional keys can be defined
            template: $YAMLPATH/simple.html   # Optional login template
```

This setup is useful only for testing. It stores passwords in plain text.
**DO NOT USE IT IN PRODUCTION.**

You can access user information via `handler.get_session()`. For user `alpha`,
this would return `{'user': 'alpha', 'id': 'alpha'}`. For user `gamma`, this
mapping would also have attributes `'role': 'user'` and `'password': 'pwd'`.

The `template:` key is optional, but you should generally associate it with a
[HTML login form file](simple) that requests a username and password (with an
[xsrf][xsrf] field). See [login templates](#login-templates) to learn how to
create one.


## Google auth

This configuration creates a [Google login page](google):

```yaml
url:
    login/google:
        pattern: /$YAMLURL/google   # Map this URL
        handler: GoogleAuth         # to the GoogleAuth handler
        kwargs:
            key: YOURKEY            # Set your app key
            secret: YOURSECRET      # Set your app secret
```

To get the application key and secret:

- Go to the [Google Dev Console](http://console.developers.google.com)
- Select a project, or create a new one.
- Enable the Google+ API service
- Under Credentials, create credentials for an OAuth client ID for a Web application
- Set the Authorized redirect URIs to point to your auth handler. (You can ignore Authorized Javascript origins)
- Copy the "Client secret" and "Client ID" to the application settings

<div class="example">
  <a class="example-demo" href="gmail/">Google Auth example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gmail/">Source</a>
</div>

You can get access to Google APIs by specifying a scope. For example, this [accesses your contacts and mails](googleapi.html):

```yaml
url:
    login/google:
        pattern: /$YAMLURL/google   # Map this URL
        handler: GoogleAuth         # to the GoogleAuth handler
        kwargs:
            key: YOURKEY            # Set your app key
            secret: YOURSECRET      # Set your app secret
            # Scope list: https://developers.google.com/identity/protocols/googlescopes
            scope:
                - https://www.googleapis.com/auth/contacts.readonly
                - https://www.googleapis.com/auth/gmail.readonly
```

The bearer token is available in the session key `google_access_token`. You can
use this with [ProxyHandler to access Google APIs](../proxyhandler/#google-proxyhandler) .

Programmatically, you can pass this to any Google API with a
`Authorization: Bearer <google_access_token>` HTTP header, or with a
`?access_token=<google_access_token>` query parameter. For example, this code
[fetches Google contacts](googleapi.html):

```python
@tornado.gen.coroutine
def contacts(handler):
    result = yield async_http_client.fetch(
        'https://www.google.com/m8/feeds/contacts/default/full',
        headers={'Authorization': 'Bearer ' + handler.session.get('google_access_token', '')},
    )
    raise tornado.gen.Return(result)
```

### SSL certificate error

Google auth and connections to HTTPS sites may fail with a
`CERTIFICATE_VERIFY_FAILED` error. Here are possible solutions:

1. Run `conda update python` to upgrade to the latest version of Python, which will use the latest `ssl` module.
2. Run `conda install certifi==2015.04.28` to downgrade to an older version of `certifi`. See this [Tornado issue](https://github.com/tornadoweb/tornado/issues/1534#issuecomment-183962419)


## Facebook auth

This configuration creates a [Facebook login page](facebook):

```yaml
url:
    login/facebook:
        pattern: /$YAMLURL/facebook # Map this URL
        handler: FacebookAuth       # to the FacebookAuth handler
        kwargs:
            key: YOURKEY            # Set your app key
            secret: YOURSECRET      # Set your app secret
```

- Go to the [Facebook apps page](https://developers.facebook.com/apps/)
- Select an existing app, or add a new app. Select website. You can skip the quick start.
- In the Settings > Basic tab on the left
  - Select Add Platform (+) > Website. Add the URL of your page. When testing, using `http://localhost:9988/` not `http://127.0.0.1:9988/`.
  - Set the app domain of your server. (When testing locally, this will be `localhost`)
- Copy the Application ID and App secret to the application settings
- If you need an `access_token` for [FacebookGraphHandler](../facebookgraphhandler/), go to Settings > Advanced and copy the Client Token


## Twitter auth

This configuration creates a [Twitter login page](twitter):

```yaml
url:
    login/twitter:
        pattern: /$YAMLURL/twitter  # Map this URL
        handler: TwitterAuth        # to the TwitterAuth handler
        kwargs:
            key: YOURKEY            # Set your app key
            secret: YOURSECRET      # Set your app secret
```

- Go to the [Twitter app page](https://apps.twitter.com/)
- Select Create New App
- Enter a Name, Description and Website
- In the Callback URL, enter the URL of the auth handler
- Go to the Keys section of the app
- Copy the Consumer Key (API Key) and Consumer Secret (API Secret) to the application settings


## LDAP auth

There are 2 ways of logging into an LDAP server.

1. **Direct** login with a user ID and password directly.
2. **Bind** login as a "bind" user, search for an ID, and then validate the password

The first method is simpler. The second is flexible -- it lets you log in with
attributes other than the username. For example, you can log in with an employee
ID or an email ID, etc instead of the "uid".

### Direct LDAP login

This configuration creates a [direct LDAP login page](ldap):

```yaml
auth/ldap:
    pattern: /$YAMLURL/ldap             # Map this URL
    handler: LDAPAuth                   # to the LDAP auth handler
    kwargs:
        template: $YAMLPATH/ldap.html   # Optional login template
        host: 10.20.30.40               # Server to connect to
        use_ssl: true                   # Whether to use SSL (LDAPS) or not
        user: 'DOMAIN\{user}'           # Check LDAP domain name with client IT team
        password: '{password}'          # This is the field name, NOT the actual password
```

The `user:` and `password:` configuration in `gramex.yaml` maps form fields to
the user ID and password. Strings inside `{braces}` are replaced by form fields
-- so if the user enters `admin` in the `user` field, `GRAMENER\{user}` becomes
`GRAMENER\admin`.

The optional `template:` should be a [HTML login form](ldap) that requests a
username and password. (The form should have an [xsrf][xsrf] field).

LDAP runs on port 389 and and LDAPS runs on port 636. If you have a non-standard
port, specify it like `port: 100`.

### LDAP attributes

**v1.23**. You can fetch additional
[additional LDAP attributes](http://www.computerperformance.co.uk/Logon/active_directory_attributes.htm)
like:

- `sAMAccountName`: user's login ID
- `CN` (common name) is the same as `name`, which is first name + last name
- `company`, `department`, etc.

To fetch these, add a `search:` section. Below is a real-life example:

```yaml
template: $YAMLPATH/ldap.html
host: 10.20.30.40                       # Provided by client IT team
use_ssl: true
user: 'ICICIBANKLTD\{user}'             # Provided by client IT team
password: '{password}'                  # This is the field name, not the actual passsword
search:                                 # Look up user attributes by searching
    base: 'dc=ICICIBANKLTD,dc=com'      # Provided by client IT team
    filter: '(sAMAccountName={user})'   # Provided by client IT team
    user: 'ICICIBANKLTD\{sAMAccountName}'   # How the username is displayed
```

- `base:` where to search. Typically `dc=DOMAIN,dc=com` for ActiveDirectory
- `filter:` what to search for. Typically `(sAMAccountName={user})` for ActiveDirectory
- `user:` what to replace the user ID with. This is a string template. If you
  want `handler.current_user['id']` to be like `DOMAIN\username`, use
  `DOMAIN\{sAMAccountName}`.

### Bind LDAP login

This configuration creates a [bind LDAP login page](ldap-bind):

```yaml
auth/ldap-bind:
    pattern: /$YAMLURL/ldap-bind            # Map this URL
    handler: LDAPAuth                       # to the LDAP auth handler
    kwargs:
        template: $YAMLPATH/ldap.html       # This has the login form
        host: ipa.demo1.freeipa.org         # Server to connect to
        use_ssl: true                       # Whether to use SSL or not
        bind:                               # Bind to the server with this ID/password
            user: 'uid=admin,cn=users,cn=accounts,dc=demo1,dc=freeipa,dc=org'
            password: $LDAP_PASSWORD        # Stored in a Gramex / environment variable
        search:
            base: 'dc=demo1,dc=freeipa,dc=org'  # Search within this domain
            filter: '(mail={user})'             # by email ID, rather than uid
            password: '{password}'              # Use the password field as password
```

This is similar to [direct LDAP login](#direct-ldap-login), but the sequence followed is:

1. Gramex logs in as (`bind.user`, `bind.password`).
2. When the user submits the form, Gramex searches the LDAP server under
   `search.base` for `search.filter` -- which becomes
   `(mail={whatever-username-was-entered})`.
3. Finally, Gramex checks if the first returned user matches the password.

[xsrf]: ../filehandler/#xsrf


## Database auth

This is the minimal configuration that lets you log in from an Excel file:

```yaml
url:
  auth/db:
    pattern: /db                          # Map this URL
    handler: DBAuth                       # to the DBAuth handler
    kwargs:
        url: $YAMLPATH/auth.xlsx          # Pick up list of users from this XLSX (or CSV) file
        user:
            column: user                  # The user column in users table has the user ID
        password:
            column: password              # The users.password column has the password
        redirect:                         # After logging in, redirect the user to:
            query: next                   #      the ?next= URL
            header: Referer               # else the Referer: header (i.e. page before login)
            url: /$YAMLURL/               # else the home page of current directory
```

Now create an `auth.xlsx` with the first sheet like this:

    user      password
    -----     --------
    alpha     alpha
    beta      beta
    ...       ...

With this, you can log into `/db` as `alpha` and `alpha`, etc. It displays a
[minimal HTML template][auth-template] that asks for an ID and password, and
matches it with the `auth.xlsx` database.

<div class="example">
  <a class="example-demo" href="dbsimple">DBAuth example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>

[auth-template]: http://code.gramener.com/cto/gramex/blob/master/gramex/handlers/auth.template.html

You can configure several aspects of this flow. You can (and *should*) use:

- `template:` to customize the appearance of the login page
- `url:` to a SQLAlchemy database (with `table:`) instead of using CSV / Excel files
- `password.function:` to encrypt the password
- `delay:` to specify the login failure delay

Here is a more complete example:

```yaml
url:
    auth/db:
    pattern: /$YAMLURL/db                 # Map this URL
    handler: DBAuth                       # to the DBAuth handler
    kwargs:
        url: sqlite:///$YAMLPATH/auth.db  # Pick up list of users from this sqlalchemy URL
        table: users                      # ... and this table (may be prefixed as schema.users)
        template: $YAMLPATH/dbauth.html   # Optional login template
        user:
            column: user                  # The users.user column is matched with
            arg: user                     # ... the ?user= argument from the form
        delay: [1, 2, 5, 10]              # Delay for failed logins
        password:
            column: password              # The users.password column is matched with
            arg: password                 # ... the ?password= argument from the form
            # You should encrypt passwords when storing them.
            # The function below specifies the encryption method.
            # Remember to change secret-key to something unique
            function: passlib.hash.sha256_crypt.encrypt(content, salt="secret-key")
```

<div class="example">
  <a class="example-demo" href="db">DBAuth example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>

You should create a [HTML login form](db) that requests a username and password
(with an [xsrf][xsrf] field). See [login templates](#login-templates) to learn
how to create one.

In the `gramex.yaml` configuration above, the usernames and passwords are stored
in the `users` table of the SQLite `auth.db` file. The `user` and `password`
columns of the table map to the `user` and `password` query arguments.
Here is sample code to populate it:

```python
engine = sqlalchemy.create_engine('sqlite:///auth.db', encoding='utf-8')
engine.execute('CREATE TABLE users (user text, password text)')
engine.execute('INSERT INTO users VALUES (?, ?)', [
    ['alpha', 'alpha'],
    ['beta', 'beta'],
    # ...
])
```

The password supports optional encryption. Before the password is compared with
the database, it is transformed via the `function:` provided. This function has
access to 2 pre-defined variables:

1. `handler`: the Handler object
1. `content`: the user-provided password

For an example of how to create users in a database, see `create_user_database`
from [authutil.py](authutil.py).

If user login fails, the response is delayed to slow down password guessing
attacks. `delay:` is a list of the delay durations. `delay: [1, 1, 5]` is the
default. This means:

- Delay for 1 second on the first failure
- Delay for 1 second on the second failure
- Delay for 5 seconds on any failure thereafter.

### Forgot password

`DBAuth` has a forgot password feature. The minimal configuration required is
below:

    url:
      auth/db:
        pattern: /db
        handler: DBAuth
        kwargs:
            url: sqlite:///$YAMLPATH/auth.db
            table: users
            user:
                column: user
            password:
                column: password
            forgot:
                email_from: gramex-guide-gmail    # Name of the email service to use for sending emails

Just add a `forgot:` section with an `email_from:` parameter that points to the
same of an [email service](../email/).

The `forgot:` section takes the following parameters (default values are shown):

- `email_from: ...`. This is mandatory. Create an [email service](../email/) and
  mention the name of the service here. Forgot password emails will be sent via
  that service. (The sender name will be the same as that service.)
- `email_as: null`. If the From: email ID is different from the user in the
  `email_as:` service, use `email_as: user@example.org`. When using GMail, you
  should [allow sending email from a different address][send-as]
- `minutes_to_expiry: 15`. The number of minutes after which the token expires.
- `template: forgot.template.html`. The name of the template file used to render
  the forgot password page. Copy [forgot.template.html][forgot-template] and
  modify it as required. Specify the path to your template in `template:`
- `arg: email`. The forgot password template allows the user to enter an email
  or a user ID. The name of the email argument is configured by `arg:`. (The
  name of the user ID argument is already specified in `user.arg`)
- `email_column: email`. The name of the email column in the database table.
- `email_text: ...`. The text of the email that is sent to the user. This is a
  template string where `{reset_url}` is replaced with the password reset URL.
  You can use any database table columns as keys. For example, if the user ID is
  in the `user` column, `email_text: {user} password reset link is {reset_url}`
  will replace `{user}` with the value in the user column, and `{reset_url}`
  with the actual password reset URL.
- `email_subject: ...`. The subject of the email that is sent to the user. This
  is a template similar to `email_text`.
- `key: forgot`. By default, the forgot password URL uses a `?forgot=`. You can
  change that to any other key.

Here is a more complete example:

```yaml
forgot:
    email_from: gramex-guide-auth     # Name of the email service to use for sending emails
    key: forgot                       # ?forgot= is used as the forgot password parameter
    arg: email                        # ?email= is used to submit the email ID of the user
    minutes_to_expiry: 15             # Minutes after which the link will expire
    email_column: email               # The database column that contains the email ID
    email_subject: Gramex forgot password       # Subject of the email
    email_as: "S Anand <root.node@gmail.com>"   # Emails will be sent as if from this ID
    email_text: |
        This is an email from Gramex guide.
        You clicked on the forgot password like for user {user}.
        Visit this link to reset the password: {reset_url}
```

<div class="example">
  <a class="example-demo" href="db">Forgot password example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>

[forgot-template]: http://code.gramener.com/cto/gramex/blob/master/gramex/handlers/forgot.template.html
[send-as]: https://support.google.com/mail/answer/22370?hl=en

### Sign up

`DBAuth` has a new user self-service sign-up feature. It lets users enter their
user ID, email and other attributes. It generates a random password and mails
their user ID (using the [forgot password](#forgot-password) feature).

Here is a minimal configuration. Just add a `signup: true` section to enable signup.

```yaml
url:
    auth/db:
    pattern: /db
    handler: DBAuth
    kwargs:
        url: sqlite:///$YAMLPATH/auth.db
        table: users
        user:
            column: user
        password:
            column: password
        forgot:
            email_from: gramex-guide-gmail
        signup: true            # Enable signup
```

<div class="example">
  <a class="example-demo" href="db?signup">Sign-up example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>

You can pass additional configurations to sign-up. For example:

```yaml
signup:
    key: signup                     # ?signup= is used as the signup parameter
    template: $YAMLPATH/signup.html # Use this signup template
    columns:                        # Mapping of URL query parameters to database columns
        name: user_name             # ?name= is saved in the user_name column
        gender: user_gender         # ?gender= is saved in the user_gender column
                                    # Other than email, all other columns are ignored
    validate: app.validate(args)    # Optional validation method is passed handler.args
                                    # This may raise an Exception or return False to stop.
```

- `key: signup` shows the signup form when the URL has a `?signup`. `key: signup`
  is the default.
- `template: signup.template.html`. The name of the template file used to render
  the signup page. Copy [signup.template.html][signup-template] and
  modify it as required. Specify the path to your template in `template:`
- `columns: {}`. The URL query parameters that should be added as columns the
  auth DB. E.g., `columns: {age: user_age}` will save the `<input name="age">`
  value in the column `user_age`.
- `validate: expression(handler, args)`. Runs any expression using `handler`
  and/or `args` as pre-defined variables. If the result is false-y, raises a HTTP
  400: Bad Request. The result is passed to the template as an `error` variable.

[signup-template]: http://code.gramener.com/cto/gramex/blob/master/gramex/handlers/signup.template.html


## Integrated auth

IntegratedAuth allows Windows domain users to log into Gramex automatically if
they've logged into Windows.

To set this up, run Gramex on a Windows domain server.
[Create one if required](https://www.youtube.com/watch?v=o6I77cz4EE4).
Then use this configuration:

```yaml
auth/integrated:
    pattern: /$YAMLURL/integrated
    handler: IntegratedAuth
```

The user must first trust this server by enabling
[SSO on IE/Chrome](http://docs.aws.amazon.com/directoryservice/latest/admin-guide/ie_sso.html)
or [on Firefox](https://wiki.shibboleth.net/confluence/display/SHIB2/Single+sign-on+Browser+configuration).
Then visiting `/integrated` will automatically log the user in. The user object
looks like this:

```js
{
    "id": "EC2-175-41-170-\\Administrator", // same as domain\username
    "domain": "EC2-175-41-170-",            // Windows domain name
    "username": "Administrator",            // Windows user name
    "realm": "WIN-8S90I248M00"              // Windows hostname
}
```

## SAML Auth

**v1.29**. SAML auth uses a [SAML](https://en.wikipedia.org/wiki/Security_Assertion_Markup_Language)
auth provided to log in. For example ADFS (Active Directory Federation Services)
is a SAML auth provider. Caveats:

- This needs the [onelogin SAML module](https://github.com/onelogin/python3-saml),
  which *is **not** installed* as part of Gramex.
- It only works on Python 3.x.
- It is **experimental** and not fully tested.

```bash
# Replace the below line with the relevant version for your system
pip install https://ci.appveyor.com/api/buildjobs/gt2betq01a5xogo7/artifacts/xmlsec-1.3.48.dev0-cp36-cp36m-win_amd64.whl
pip install python3-saml
```

This configuration enables SAML authentication.

```yaml
auth/saml:
    pattern: /$YAMLURL/login
    handler: SAMLAuth
        kwargs:
          xsrf_cookies: false                   # Disable XSRF. SAML cannot be hacked via XSRF
          sp_domain: 'app.client.com'           # Public domain name of the gramex application
          https: true                           # true if app.client.com is on https
          custom_base_path: $YAMLPATH/saml/     # Path to settings.json and certs/
          lowercase_encoding: True              # True for ADFS driven SAML auth
```

`custom_base_path` points to a directory with these files:

- `settings.json`: Provides details of the Identity Provider (IDP, i.e. the
  server that logs in users) and Service Provider (your app). For ADFS, this can
  be extracted using the ADFS's `metadata.xml`. Here is a minimal
  [settings.json](saml/settings.json)
- `advanced_settings.json`: Contains security params and oraganisation details.
  Here is a sample [advanced_settings.json](saml/advanced_settings.json).
  `contactPerson` and `organization` are optional.
- `certs/` directory that has the certificates required for encryption.
    - `metadata.crt`: Certificate to sign the metadata of the SP
    - `metadata.key`: Key for the above certificate

Once configured, visit the auth handler with `?metadata` added to view the
service provider metadata. In the above example, this would be
`https://app.client.com/login?metadata`.

**Note:** Provide the SP metadata URL to the client for relay configuration
along with required claims (i.e. fields to be returned, such as `email_id`,
`username`, etc.)


## OAuth2

**v1.30**. Gramex lets you log in via any OAuth2 providers. This includes:

- [Facebook](https://developers.facebook.com/docs/facebook-login)
- [Github](https://developer.github.com/apps/building-oauth-apps/)
- [Gitlab](https://docs.gitlab.com/ce/api/oauth2.html)
- [Google](https://developers.google.com/identity/protocols/OAuth2)
- [Instagram](https://www.instagram.com/developer/authentication/)
- [LinkedIn](https://developer.linkedin.com/docs/oauth2)
- [SalesForce](https://goo.gl/hVzQYL)
- [StackOverflow](https://api.stackexchange.com/docs/authentication)

Here is a sample configuration for Gitlab:

```yaml
url:
  auth/gitlab:
    pattern: /$YAMLURL/gitlab
    handler: OAuth2
    kwargs:
      # Create app at https://code.gramener.com/admin/applications/
      client_id: 'YOUR_APP_CLIENT_ID'
      client_secret: 'YOUR_APP_SECRET_ID'
      authorize:
        url: 'https://code.gramener.com/oauth/authorize'
      access_token:
        url: 'https://code.gramener.com/oauth/token'
        body:
          grant_type: 'authorization_code'
      user_info:
        url: 'https://code.gramener.com/api/v4/user'
        headers:
          Authorization: 'Bearer {access_token}'
```

<div class="example">
  <a class="example-demo" href="gitlab">Gitlab OAuth2 example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>

It accepts the following configuration:

- `client_id`: Create an app with the OAuth2 provider to get this ID
- `client_secret`: Create an app with the OAuth2 provider to get this ID
- `authorize`: Authorization endpoint configuration:
    - `url`: Authorization endpoint URL
    - `scope`: an optional a list of string scopes that determine what you can access
    - `extra_params`: an optional dict of URL query params passed
- `access_token`: Access token endpoint configuration
    - `url`: Access token endpoint URL
    - `session_key`: optional key in session to store access token information. default: `access_token`
    - `headers`: optional dict containing HTTP headers to pass to access token URL. By default, sets `User-Agent` to `Gramex/<version>`.
    - `body`: optional dict containing arguments to pass to access token URL (e.g. `{grant_type: authorization_code}`)
- `user_info`: Optional user information API endpoint
    - `url`: API endpoint to fetch URL
    - `headers`: optional dict containing HTTP headers to pass to user info URL. e.g. `Authorization: 'Bearer {access_token}'`. Default: `{User-Agent: Gramex/<version>}`
    - `method`: HTTP method to use. default: `GET`
    - `body`: optional dict containing POST arguments to pass to user info URL
    - `user_id`: Attribute in the returned user object that holds the user ID. This is used to identify the user uniquely. default: `id`
- `user_key`: optional key in session to store user information. default: `user`

<div class="example">
  <a class="example-demo" href="github">Github OAuth2 example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>

<div class="example">
  <a class="example-demo" href="googleoauth2">Google OAuth2 example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>


## Log out

This configuration creates a [logout page](logout?next=.):

```yaml
auth/logout
    pattern: /$YAMLURL/logout   # Map this URL
    handler: LogoutHandler      # to the logout handler
```

After logging in, users are re-directed to the `?next=` URL. You can change this
using the [redirection configuration](../config/#redirection).


# Authentication features

## Login templates

Several auth mechanisms (such as [SimpleAuth](#simple-auth),
[LDAPAuth](#ldap-auth), [DBAuth](#database-auth)) use a template to request the
user ID and password. This is a minimal template:

```html
<form method="POST">
    {% if error %}<p>error code: {{ error['code'] }}, message: {{ error['error'] }}</p>{% end %}
    <input name="user">
    <input name="password" type="password">
    <input type="hidden" name="_xsrf" value="{{ handler.xsrf_token }}">
    <button type="submit">Submit</button>
</form>
```

If `error` is set, we display the `error['code']` and `error['error']`.
Otherwise, we have 3 input fields:

- `user`: the user name. By default, the name of the field should be `user`, but this can be configured
- `password`: the password. The name of this field can also be configured
- `_xsrf`: the [XSRF][xsrf] token for this request.

## AJAX login

To using an AJAX request to log in, use this approach:

```js
$('form').on('submit', function(e) {
  e.preventDefault()
  $('#message').append('<div>Submitting form</div>')
  $.ajax('simple', {
    method: 'POST',
    data: $('form').serialize()
  }).done(function () {
    $('#message').append('<div>Successful login</div>')
  }).fail(function (xhr, status, message) {
    $('#message').append('<div>Failed login: ' + message + '</div>')
  })
})
```

**Note**: when using AJAX, `redirect:` does not change the main page. The
`.done()` method will get the contents of the redirected page as a HTML string.
To redirect on success, change `window.location` in `.done()`.

<div class="example">
  <a class="example-demo" href="ajax.html">AJAX auth example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>


## Login actions

When a user logs in or logs out, you can register actions as follows:

```yaml
url:
    login/google:
    pattern: /$YAMLURL/google
    handler: GoogleAuth
    kwargs:
        key: YOURKEY
        secret: YOURSECRET
        action:                                     # Run multiple function on Google auth
        -
            function: ensure_single_session         # Logs user out of all other sessions
        -
            function: sys.stderr.write('Logged in via Google')      # Write to console
```

For example, the [ldap login](ldap) page is set with `ensure_single_session`.
You can log in on multiple browsers. Every log in will log out other sessions.

You can write your own custom functions. By default, the function will be passed
the `handler` object. You can define any other `args` or `kwargs` to pass
instead. The actions will be executed in order.

When calling actions, `handler.current_user` will have the user object on all
auth handlers and the `LogoutHandler`.

## User attributes

All handlers store the information retrieved about the user in
`handler.session['user']`, typically as a dictionary. All handlers have access
to this information via `handler.current_user` by default.

Typically, users log into only one AuthHandler, like DBAuth or GoogleAuth.
Sometimes you want to log into both -- for example, to access the Google APIs.
For this, you can specify a `user_key: something`. This stores the user object
in `handler.session['something']` instead of `handler.session['user']`. This
applies to all Auth handlers including [LogoutHandler](#logouthandler). For
example:

```yaml
url:
  googleauth:
    pattern: /google
    handler: GoogleAuth
    kwargs:
      user_key: google_user    # Store user info in session.google_user not session.user
      # ...

  twitterauth:
    pattern: /twitter
    handler: TwitterAuth
    kwargs:
      user_key: twitter_user   # Store user info in session.twitter_user
      # ...
```


## Logging logins

See [user logging](../config/#user-logging).

## Session expiry

Gramex sessions expire in 31 days by default. This is configured under
`app.session.expiry`.

All auth handlers accept a `session_expiry: <days>` kwarg that changes the expiry
date when the user logs in with that handler. For example:

```yaml
url:
    auth/expiry:
        pattern: /$YAMLURL/expiry
        handler: SimpleAuth
        kwargs:
            session_expiry: 0.0003          # Session expires in 26 seconds
            credentials: {alpha: alpha}
```

<div class="example">
  <a class="example-demo" href="expiry">Session expiry example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>

This can be used to configure sessions that have a long expiry (e.g. for mobile
applications) or short expiry (e.g. for secure data applications.)

To allow users to choose how long to stay logged in, use:

```yaml
url:
    auth/customexpiry:
        pattern: /$YAMLURL/customexpiry
        handler: SimpleAuth
        kwargs:
            session_expiry:
                default: 4      # the default session expiry is set to 4 days
                key: remember   # When ?remember= is submitted on login
                values:         # if ?remember=...
                    day: 1          # ...day, it expires in 1 day
                    week: 7         # ...week, it expires in 7 days
                    month: 31       # ...month, it expires in 31 days
```

<div class="example">
  <a class="example-demo" href="customexpiry">Remember me example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>

## Inactive expiry

Gramex sessions expire if the user is inactive, i.e. has not accessed Gramex, for
a number of days.

By default, this is not enabled. You can add `session_inactive: <days>` to
any Auth handler. When the user logs in with that handler, their session will
expire unless they visit again within `<days>` days. For example:

```yaml
url:
    auth/expiry:
        pattern: /$YAMLURL/expiry
        handler: SimpleAuth
        kwargs:
            session_inactive: 0.0003         # Must visit every 26 seconds
            credentials: {alpha: alpha}
    other/pages:
        ...
        kwargs:                              # Ensure that other authenticated pages
            headers:                         # also expire every 26 seconds
                Cache-Control: private, max-age=26
```

<div class="example">
  <a class="example-demo" href="inactive">Inactive expiry example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>


## Change inputs

All auth handlers support a `prepare:` function. You can use this to modify the
inputs passed by the user. For example:

- If the username is encrypted and you want to decrypt it
- To add the domain name before the user, e.g. user types USERNAME, you change it to DOMAIN\USERNAME
- To restrict the login to specific IP addresses

The YAML configuration is:

```yaml
url:
    auth/login:
        pattern: /$YAMLURL/login/
        handler: ...                # Any auth handler can be used
        kwargs:
            ...                     # Add parameters for the auth handler
            prepare: module.function(args, handler)
```

You can create a `module.py` with a `function(args, handler)` that modifies the
arguments as required. For example:

```python
def function(args, handler):
    if handler.request.method == 'POST':
        args['user'][0] = 'DOMAIN\\' + args['user'][0]
        args['password'][0] = decrypt(args['password'][0])
        # ... etc
```

The changes to the arguments will be saved in `handler.args`, which all auth
handlers use. (NOTE: These changes need not affect `handler.get_argument()`.)

## Lookup attributes

Each auth handler creates a `handler.session['user']` object. The keys in this
object can be extended from any data source. For example, create a `lookup.xlsx`
file with this data:

| user  | gender |
|-------|--------|
| alpha | male   |
| beta  | female |

Add a `lookup` section to any auth handler and specify a `url: lookup.xlsx`. For
example:

```yaml
url:
    auth/lookup-attributes:
        pattern: /$YAMLURL/lookup-attributes
        handler: SimpleAuth
        kwargs:
            credentials:
                alpha: alpha
                beta: beta
            lookup:
                url: $YAMLPATH/lookup.xlsx      # Add attributes from Excel file
                id: user                        # by lookup up the 'id' in the 'user' column
```

<div class="example">
  <a class="example-demo" href="lookup-attributes">Lookup attributes example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/gramex.yaml">Source</a>
</div>

Click on the link above and see the new session object on this page. If you
logged in as `alpha` or `beta`, you will see a `gender` of `male` or `female`
respectively. This is picked up from the Excel file.

This looks up the user's `id` in the `user` column of Excel. You can change the
column name by changing `lookup.id` as in the example above.

All columns in the Excel sheet are added as attributes. But if a value is NULL
(not an empty string), it is ignored. In Excel, deleting a cell makes it NULL.

By default, this looks up the first sheet. You can specify an alternate sheet
using `sheetname: ...`. For example:

```yaml
        lookup:
            url: $YAMLPATH/lookup.xlsx
            sheetname: userinfo             # Specify an alternate sheet name
            id: user
```

Instead of Excel files, you can use databases by specifying:

```yaml
        lookup:
            url: sqlite:///$YAMLPATH/database.sqlite3
            table: lookup
```

The kwargs for lookup are the same as for [FormHandler](../formhandler/).


# Automated logins

Gramex has two mechanisms to automate logins: [one-time passwords](#otp) and [encrypted users](#encrypted-user).

## OTP

Handlers support a `handler.otp(expire=seconds)` function. This returns a
one-time password string linked to the *current user*. When you send a request
with a `X-Gramex-OTP: <otp>` header or a `?gramex-otp=<otp>` query parameter,
that session is automatically linked to the same user.

<div class="example">
  <a class="example-demo" href="otp">OTP example</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/auth/otp.html">Source</a>
</div>

## Encrypted user

You can mimic a user by passing a `X-Gramex-User` HTTP header. This must be
encrypted via an OpenSSH RSA key. To set this up:

1. Run `ssh-keygen -t rsa -N "" -f .id_rsa`. This creates a private key
   `.id_rsa` and a public key `id_rsa.pub`. Keep both secure. Do not distribute
   either. (You can use an existing key pair too.)
2. Add a top level `encrypt:` section to your `gramex.yaml`:

```yaml
encrypt:
    public_key: $YAMLPATH/.id_rsa.pub   # Path to the public key
    private_key: $YAMLPATH/.id_rsa      # Path to the private key
```

To get the encrypted for a user, run this from a command line:

```python
from gramex.services import encrypt
encrypter = encrypt({
    'public_key': '/path/to/.id_rsa.pub',
    'private_key': '/path/to/.id_rsa',
})
# This is the user object we want to mimic
user = {'id': 'user@example.org', 'role': 'manager'}
# Get the encrypted user key as a long string, e.g. rx5/NQV1lXaA0QI...
user_key = encrypter.encrypt(user)
# Decrypt the user key. The decrypted user will be the same as user
decrypted_user = encrypter.decrypt(user_key)
```

To mimic this user, send the encrypted user key with the HTTP header
`X-Gramex-User:`. For example:

```python
r = requests.get('http://127.0.0.1/my-gramex-url', headers={
    'X-Gramex-User': encrypter.encrypt({'id': 'user@example.org', 'role': 'manager'})
})
```

This fetches the URL as if the `user@example.org` user with `manager` role was
logged in.

This mechanism is internally used in [Smart Alerts](../alert/) and
[CaptureHandler](../capturehandler/) to take a screenshot as a specific user. (WIP)


# Authorization

To restrict pages to specific users, use the `kwargs.auth` configuration. This
works on all Gramex handlers (that derive from `BaseHandler`).

If you don't specify `auth:` in the `kwargs:` section, the `auth:` defined in
`app.settings` will be used. If that's not defined, then the handler is publicly
accessible to all.

`auth: true` just requires that you must log in. In this example, you can access
[must-login](must-login) only if you are logged in.

```yaml
url:
    auth/must-login:
        pattern: /$YAMLURL/must-login
        handler: FileHandler
        kwargs:
            path: $YAMLPATH/secret.html
            auth: true
```

You can restrict who can log in using [roles](#roles) or any other condition.

## Login URLs

By default, this will redirect users to `/login/`. This is configured in the `app.settings.login_url` like this:

```yaml
app:
    settings:
        login_url: /$YAMLURL/login/   # This is the default login URL
```

You need to either map `/login/` to an auth handler, or change the `login_url`
to your auth handler URL.

Each URL can choose its own login URL. For example, if you
[logout](logout?next=.) and visit [use-simple](use-simple), you will always be
taken to `auth/simple` even though `app.settings.login_url` is `/login/`:

```yaml
url:
    auth/protected-page:
        pattern: /$YAMLURL/protected-page
        handler: FileHandler
        kwargs:
            path: $YAMLPATH/protected-page.html
            auth:
                login_url: /$YAMLURL/login  # Redirect users to this login page
```

For AJAX requests (that send an [X-Requested-With header](https://en.wikipedia.org/wiki/List_of_HTTP_header_fields#Common_non-standard_request_fields))
redirection is disabled - since AJAX cannot redirect the parent page. So:

```js
$.ajax('protected-page')
  .done(function() { ... })     // called if protected page returns valid data
  .fail(function() { ... })     // called if auth failed.
```

To manually disable redirection, set `login_url: false`.

## Roles

`auth:` can check for membership. For example, you can access [en-male](en-male)
only if your gender is `male` and your locale is `en` or `es`. (To test it,
[logout](logout?next=.) and [log in via Google](google).)

```yaml
    auth:
        membership:           # The following user object keys must match
            gender: male      # user.gender must be male
            locale: [en, es]  # user.locale must be en or es
            email: [..., ...] # user.email must be in in this list
```

If the `user` object has nested attributes, you can access them via `.`. For
example, `attributes.cn` refers to `handlers.current_user.attributes.cn`.

You can specify multiple memberships that can be combined with AND or OR. This example allows (Females from @gramener.com) OR (Males with locale=en) OR (beta@example.org):

```yaml
    auth:
        membership:
            -                           # First rule
                gender: female                # Allow all women
                hd: [ibm.com, pwc.com]        # AND from ibm.com or pwc.com
            -                           # OR Second rule
                gender: male                  # Allow all men
                locale: [en, es]              # with user.locale as "en" or "es"
            -                           # OR Third rule
                email: beta@example.org       # Allow this user
```

`auth:` lets you define conditions. For example, you can access [dotcom](dotcom)
only if your email ends with `.com`, and access [dotorg](dotorg) only if your
email ends with `.org`.

```yaml
url:
    auth/dotcom:
        pattern: /$YAMLURL/dotcom
        handler: FileHandler
        kwargs:
            path: $YAMLPATH/secret.html
            auth:
                condition:                          # Allow only if condition is true
                    function: handler.current_user.email.endswith('.com')
    auth/dotorg:
        pattern: /$YAMLURL/dotorg
        handler: FileHandler
        kwargs:
            path: $YAMLPATH/secret.html
            auth:
                condition:                          # Allow only if condition is true
                    function: handler.current_user.email.endswith('.org')
```

You can specify any function of your choice. The function must return (or yield)
`True` to allow the user access, and `False` to raise a HTTP 403 error.

To repeat auth conditions across multiple handlers, see [Reusing Configurations](#reusing-configurations).


## Templates for unauthorized

When a user is logged in but does not have access to the page (because of the
`auth` condition or membership), you can display a friendly message using
`auth.template`. Visit [unauthorized-template](unauthorized-template) for an
example. You will see the contents of `403-template.html` rendered.

```yaml
url:
    auth/unauthorized-template:
        pattern: /$YAMLURL/unauthorized-template
        handler: FileHandler
        kwargs:
            path: $YAMLPATH/secret.html
            auth:
                membership:                     # Pick an unlikely condition to test template
                    donkey: king                # This condition will usually be false
                template: $YAMLPATH/403-template.html   # Render template for forbidden users
```
