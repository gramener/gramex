title: Configuration reference

This is an annotated `gramex.yaml` that documents all aspects of the Gramex
configuration. Default values are shown.

    :::yaml
    # Gramex APIs are versioned. The version key is required. Currently, 1.0 is the
    # only version supported.
    version: 1.0

    # The `app:` section defines the settings for the Tornado application.
    # http://tornado.readthedocs.org/en/stable/web.html#tornado.web.Application.settings
    app:
        browser: False                      # Open the browser on startup
        debug_exception: False              # Start pdb on exception
        listen:
            port: 9988                      # Port to bind to. (8888 used by Jupyter)
            xheaders: True                  # X-Real-Ip/X-Forwarded-For and X-Scheme/X-Forwarded-Proto override remote IP, scheme
            max_buffer_size: 1000000000     # Max length of data that can be POSTed
            max_header_size: 1000000000     # Max length of header that can be received
            max_body_size: 1000000000       # Max length of data that can be uploaded
        settings:                           # Tornado app settings
            # default_host: 'host'          # Optional name of default host

            # Debug parameters
            autoreload: False               # Reload Gramex when imported Python file changes
            compiled_template_cache: True   # Cache template files across requests
            static_hash_cache: True         # Cache static files across requests
            serve_traceback: True           # Show traceback on browser if there's an error
            debug: False                    # = autoreload + !compiled_template_cache + !static_hash_cache + serve_traceback

            # Cookie parameters
            xsrf_cookies: True              # Reject POST/PUT/DELETE unless _xsrf header / form input is present
            cookie_secret: secret-key       # Encrypt cookies with this secret key
            key_version: 2                  # Cookie encryption version. 2 is the latest

            # Template parameters
            autoescape: True                # Escape HTML tags in templates
            template_path: .                # Default location of templates (not currently used)
            static_path: './static'         # Local path for static files (not currently used)
            static_url_prefix: '/static/'   # URL prefix for static files (not currently used)

            # Login parameters
            login_url: /login               # URL used to log in
            twitter_consumer_key: ...       # For Twitter login
            twitter_consumer_secret: ...    # For Twitter login
            google_consumer_key: ...        # For Google login
            google_consumer_secret: ...     # For Google login
            facebook_api_key: ...           # For Facebook login
            facebook_secret: ...            # For Facebook login

            compress_response: True         # GZip the HTTP response

    # --------------- TODO ---------------------    
    
    # Define system caches.
    # This section MUST be before the url: section. Otherwise, the urls cannot use the cache
    cache:
        memory:
            type: memory                    # A default in-memory cache

    # Set up file watches here
    watch:
        gramex-reconfig:
            paths: $YAMLPATH
            on_modified: gramex.init
