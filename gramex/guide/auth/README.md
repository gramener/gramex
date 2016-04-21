title: Gramex Authentication

[gramex.yaml](gramex.yaml) uses GoogleAuth handler to authenticate this application. It uses the following configuration:

    app:
        settings:                                  # Tornado app settings
            auth: True                             # Enable authentication
            login_url: /login/google/              # redirect to login page
            cookie_secret: COOKIE_NAME             #
            google_oauth:                          # Google oauth keys
                key: YOURKEY                       #       use your key
                secret: YOURSECRET                 #       and secret here
    url:
        google-login:
            pattern: /login/google/                # /login/google
            handler: GoogleAuth    # use GoogleAuth hadnler

The `app:` section defines the settings for the Tornado application. And, the `url:` section tells Gramex how to map URLs to [handlers](https://learn.gramener.com/gramex/handlers.html).

The configuration below directs login to [/login/google/](/login/google/) to a GoogleAuth handler.

The `auth:` setting, cascades down to all other URL patterns (handlers) unless over-written with `auth:` under `kwargs:` parameter of `handler:` specs

    lib:
        pattern: /lib/(.*)              # Anything under /lib/
        handler: FileHandler
        kwargs:
            auth: False                 # is not authenticated
            path: "{.}/lib"             # maps to /lib/ under the Gramex source folder
                                        # {.} is replaced with the conf file's folder
            index: true                 # Allow browsing the libraries

This will make anything under /lib/ available even without logging in.

Also, you could set `app:settings:auth:` to `False` and protect certain URL patterns only too.

Read [tornado auth](http://www.tornadoweb.org/en/stable/auth.html#google) on how to register your application with Google for OAuth authorization.
