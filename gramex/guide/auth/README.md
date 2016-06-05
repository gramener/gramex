title: Gramex Authentication

## Sessions

Gramex identifies sessions through a secure cookie named `sid`, and stores
information against each session as a persistent key-value store. This is
available as `handler.session` in every handler. For example, here is the
contents of your `handler.session` variable now:

<iframe frameborder="0" src="session"></iframe>

This has a `randkey` variable that was generated using the following code:

    :::python
    def store_value(handler):
        handler.session.setdefault('randkey', random.randint(0, 1000))
        return json.dumps(handler.session)

The first time a user visits the [session](session) page, it generates the
`randkey`. The next time this is preserved.

You can store any variable against a session. These are stored in the `sid`
secure cookie for a duration that's controlled by the `app.session.expiry`
configuration in `gramex.yaml`. Here is the default configuration:

    :::yaml
    app:
      session:
        expiry: 31                      # Session cookies expiry in days


# Authentication

Gramex allows users to log in using various single sign-on methods. The flow
is as follows:

1. Define a Gramex auth handler. This URL renders / redirects to a login page
2. When the user logs in, send the credentials to the auth handler
3. If credentials are valid, store the user details and redirect the user. Else
   show an error message.

## Google

This configuration creates a [Google login page](google):

    :::yaml
    url:
        login/google:
            pattern: /$YAMLURL/google   # Map this URL
            handler: GoogleAuth         # to the GoogleAuth handler
            kwargs:
                key: YOURKEY            # Set your app key
                secret: YOURSECRET      # Set your app secret

To get the application key and secret:

- Go to the [Google Dev Console](http://console.developers.google.com)
- Select a project, or create a new one.
- Enable the Google+ API service
- Under Credentials, create credentials for an OAuth client ID for a Web application
- Set the Authorized redirect URIs to point to your auth handler. (You can ignore Authorized Javascript origins)
- Copy the "Client secret" and "Client ID" to the application settings


## Facebook

This configuration creates a [Facebook login page](facebook):

    :::yaml
    url:
        login/facebook:
            pattern: /$YAMLURL/facebook # Map this URL
            handler: FacebookAuth       # to the FacebookAuth handler
            kwargs:
                key: YOURKEY            # Set your app key
                secret: YOURSECRET      # Set your app secret

- Go to the [Facebook apps page](https://developers.facebook.com/apps/)
- Select an existing app, or add a new app. Select website. You can skip the quick start.
- In the Settings tab on the left, set the URL of of your server's home page
- Copy the Application ID and App secret to the application settings


## Twitter

This configuration creates a [Twitter login page](twitter):

    :::yaml
    url:
        login/twitter:
            pattern: /$YAMLURL/twitter  # Map this URL
            handler: TwitterAuth        # to the TwitterAuth handler
            kwargs:
                key: YOURKEY            # Set your app key
                secret: YOURSECRET      # Set your app secret

- Go to the [Twitter home page](https://apps.twitter.com/)
- Select Create New App
- Enter a Name, Description and Website
- In the Callback URL, enter the URL of the auth handler
- Go to the Keys section of the app
- Copy the Consumer Key (API Key) and Consumer Secret (API Secret) to the application settings


## LDAP

This configuration creates an [LDAP login page](ldap):

    :::yaml
    auth/ldap:
        pattern: /$YAMLURL/ldap                 # Map this URL
        handler: LDAPAuth                       # to the LDAP auth handler
        kwargs:
            template: $YAMLPATH/ldap.html       # This has the login form
            host: ipa.demo1.freeipa.org         # Server to connect to
            use_ssl: true                       # Whether to use SSL or not
            port: 636                           # Optional. Usually 389 for LDAP, 636 for LDAPS
            user: 'uid={user},cn=users,cn=accounts,dc=demo1,dc=freeipa,dc=org'
            password: '{password}'

The [login page](ldap) should provide a username, password and an [xsrf][xsrf]
field. Additional fields (e.g. for domain) are optional. The `user:` and
`password:` fields map these to the LDAP user ID and password. Strings inside
`{braces}` are replaced by form fields -- so if the user enters `admin` in the
`user` field, `uid={user},cn=...` becomes `uid=admin,cn=...`.


[xsrf]: http://www.tornadoweb.org/en/stable/guide/security.html#cross-site-request-forgery-protection

## Redirection

After users logs in, they are redirected based on the common `redirect:` section
in the auth handler kwargs. This redirect URL can be based on:

- a URL `query` parameter
- a HTTP `header`, or
- a direct `url`

For example:

    :::yaml
    url:
      login/google:
        pattern: /$YAMLURL/google
        handler: GoogleAuth
        kwargs:
          key: YOURKEY
          secret: YOURSECRET
          redirect:                 # Redirect options are applied in order
            query: next             # If ?next= is specified, use it
            header: Referer         # Else use the HTTP header Referer if it exists
            url: /$YAMLURL          # Else redirect to the directory where this gramex.yaml is present

If none of these is specified, the user is redirected to the home page `/`.

In the above configuration, [google?next=../config/](google?next=../config/)
will take you to the [config](../config/) page after logging in.

By default, the URL must redirect to the same server (for security reasons). So
[google?next=https://gramener.com/](google?next=https://gramener.com/) will
ignore the `next=` parameter. However, you can specify `external: true` to
override this:

    ::yaml
        kwargs:
          external: true

You can test this at
[ldap2?next=https://gramener.com/](ldap2?next=https://gramener.com/).
