title: Deployment patterns

Development and deployment are usually on different machines with different
configurations, file paths, database locations, etc. All of these can be
configured in `gramex.yaml` using pre-defined variables.

## Windows Installation

To install a Gramex application as a service on a Windows Server:

- [Install Anaconda and Gramex](../install/)
    - Download and install [Anaconda][anaconda] 4.4.0 or later
    - Run `pip install https://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=master`.
      (Replace ``master`` with ``dev`` for the development version).
- Install your application in any folder - via `git clone` or by copying files
- Run PowerShell or the Command Prompt **as administrator**
- From your application folder, run `gramex service install --name "App name" --desc "App description"`

Here are additional install options:

    gramex service install
        --name "Application Name"
        --desc "Long description"
        --dir  "C:/path/to/application/"    # Run Gramex in this directory
        --user "DOMAIN\USER"                # Optional user to run as
        --password "user-password"          # Required if user is specified
        --startup manual|auto|disabled      # Default is manual

The user domain and name are stored as environment variables `USERDOMAIN` and
`USERNAME`. Run `echo %USERDOMAIN% %USERNAME%` on the Command Prompt to see them.

You can update these parameters any time via:

    gramex service update --...             # Same parameters as install

To uninstall the service, run:

    gramex service remove

To start / stop / restart the application, go to Control Panel > Administrative
Tools > View Local Services and update your service. You can also do this from
the command prompt **as administrator**:

    gramex service start
    gramex service stop
    gramex service restart

Once started, the application is live at the port specified in your
`gramex.yaml`. The default port is 9988, so visit <http://localhost:9988/>. If no
`gramex.yaml` is found in the current directory, Gramex shows the Gramex Guide
(this application.)

Service logs can be viewed using the Windows Event Viewer. Gramex logs are at
`%LOCALAPPDATA%\Gramex Data\logs\` unless over-ridden by `gramex.yaml`.

[anaconda]: http://continuum.io/downloads


## Security

Some common security options are pre-configured in `$GRAMEXPATH/deploy.yaml`. To enable these options, add this line to your `gramex.yaml`:

    :::yaml
    import: $GRAMEXPATH/deploy.yaml

See [deploy.yaml](https://code.gramener.com/s.anand/gramex/blob/master/gramex/deploy.yaml) to understand the configurations.

## Relative URL mapping

Your app may be running at `http://localhost:9988/` on your system, but will be
running at `http://server/app/` on the server. Use relative URLs and paths to
allow the application to work in both places.

Suppose `/gramex.yaml` imports all sub-directories:

    :::yaml
    import: */gramex.yaml   # Import all gramex.yaml from 1st-level sub-directories

... and `/app/gramex.yaml` has:

    :::yaml
    url:
        page-name:
            pattern: /$YAMLURL/page         # Note the /$YAMLURL prefix
            handler: FileHandler
            kwargs:
                path: $YAMLPATH/page.html   # Note the $YAMLPATH prefix

When you run Gramex from `/app/`, the pattern becomes `/page` (`$YAMLURL` is `.`)

When you run Gramex from `/`, the pattern becomes `/app/page` (`$YAMLURL` is `/app`)

The correct file (`/app/page.html`) is rendered in both cases because
`$YAMLPATH` points to the absolute directory of the YAML file.

You can modify the app name using `../new-app-name`. For example, this pattern
directs the URL `/new-app-name/page` to `/app/page.html`.

    :::yaml
            pattern: /$YAMLURL/../new-app-name/page

You also need this in [redirection URLs](https://learn.gramener.com/guide/config/#redirection).
See this example:

```yaml
url:
  auth/simple:
    pattern: /$YAMLURL/simple
    handler: SimpleAuth
    kwargs:
      credentials: {alpha: alpha}
      redirect: {url: /$YAMLURL/}        # Note the $YAMLURL here
```

Using `/$YAMLURL/` redirects users back to *this* app's home page, rather than
the global home page (which may be `uat.gramener.com/`.)

**Tips**:

- `/$YAMLURL/` will always have a `/` before and after it.
- `pattern:` must always start with `/$YAMLURL/`
- `url:` generally starts with `/$YAMLURL/`


### Using relative URLs

In your HTML code, use relative URLs where possible. For example:
`http://localhost:9988/` becomes `.` (not `/` -- which is an absolute URL.)
Similarly, `/css/style.css` becomes `css/style.css`.

Sometimes, this is not desirable. For example, If you are linking to the same
CSS file from different directories, you need specifying `/style.css` is
helpful. This requires server-side templating.

You can use a [Tornado template like this](template.html.source) that using a
pre-defined variable, e.g. `APP_ROOT`.

    :::html
    <link rel="stylesheet" href="/{{ APP_ROOT }}/style.css">

In `gramex.yaml`, we pass `APP_ROOT` to the that's set to `$YAMLURL`. For example:

    :::yaml
    variables:
        APP_ROOT: $YAMLURL       # Pre-define APP_ROOT as the absolute URL to gramex.yaml's directory

    url:
        deploy-url:
            pattern: /$YAMLURL/url/(.*)               # Any URL under this directory
            handler: FileHandler                      # is rendered as a FileHandler
            kwargs:
                path: $YAMLPATH/template.html         # Using this template
                transform:
                    "template.html":
                        # Convert to a Tornado template
                        # Pass the template the APP_ROOT variable
                        function: template(content, APP_ROOT="$APP_ROOT")

To test this, open the following URLs:

- [url/main](url/main)
- [url/main/sub](url/main/sub)
- [url/main/sub/third](url/main/sub/third)

In every case, the correct absolute path for `/style.css` is used,
irrespective of which path the app is deployed at.

## Using YAMLPATH

`$YAMLPATH` is very similar to `$YAMLURL`. It is the relative path to the current
`gramex.yaml` location.

When using a `FileHandler` like this:

```yaml
url:
  app-home:
    pattern: /                  # This is hard-coded
    handler: FileHandler
    kwargs:
      path: index.html          # This is hard-coded
```

... the locations are specified relative to where Gramex is running. To make it
relative to where the `gramex.yaml` file is, use:

```yaml
url:
  app-home:
    pattern: /$YAMLURL/
    handler: FileHandler
    kwargs:
      path: $YAMLPATH/index.html        # Path is relative to this directory
```

**Tips**:

- `$YAMLPATH/` will never have a `/` before it, but generally have a `/` after it
- `path:` must always start with a `$YAMLPATH/`
- `url:` for DataHandler or QueryHandler can use it for SQLite or Blaze objects.
  For example, `url: sqlite:///$YAMLPATH/sql.db`.

### Deployment variables

[Predefined variables](../config/#predefined-variables) are useful in deployment. For example, say you have the following directory structure:

    /app              # Gramex is run from here. It is the current directory
      /component      # Inside a sub-directory, we have a component
        /gramex.yaml  # ... along with its configuration
        /index.html   # ... and a home page

Inside `/app/component/gramex.yaml`, here's what the variables mean:

    :::yaml
    url:
        relative-url:
            # This pattern: translates to /app/component/index.html
            # Note: leading slash (/) before $YAMLURL is REQUIRED
            pattern: /$YAMLURL/index.html
            handler: FileHandler
            kwargs:
                path: $YAMLPATH/        # This translates to /app/component/

If you want to refer to a file in the Gramex source directory, use
`$GRAMEXPATH`. For example, this maps [config](config) to Gramex's root
`gramex.yaml`.

    :::yaml
    url:
        gramex-config-file:
            pattern: /$YAMLURL/config           # Map config under current URL
            handler: FileHandler
            kwargs:
                path: $GRAMEXPATH/gramex.yaml   # to the core Gramex config file

Typically, applications store data in `$GRAMEXDATA/data/<appname>/`. Create and use this directory for your data storage needs.


## HTTPS Server

To set up Gramex as a HTTPS server, you need a certificate file and a key file,
both in PEM format. Use the following settings in `gramex.yaml`:

    :::yaml
    app:
        listen:
            port: 443
            ssl_options:
                certfile: "path/to/certificate.pem"
                keyfile: "path/to/privatekey.pem"

You can then connect to `https://your-gramex-server/`.

To generate a self-signed HTTPS certificate for testing, run:

    :::bash
    openssl genrsa -out privatekey.pem 1024
    openssl req -new -key privatekey.pem -out certrequest.csr
    openssl x509 -req -in certrequest.csr -signkey privatekey.pem -out certificate.pem

Or you can use these pre-created [privatekey.pem](privatekey.pem) and
[certificate.pem](certificate.pem) for localhost. (This was created with subject
`/C=IN/ST=KA/L=Bangalore/O=Gramener/CN=localhost/emailAddress=s.anand@gramener.com`
and is meant for `localhost`.)

All browsers will report that this connection is not trusted, since it is a
self-signed certificate. Ignore the warning proceed to the website.


## Proxy servers

Gramex is often deployed behind a reverse proxy. This allows a web server (like
nginx, Apache, IIS, Tomcat) to pass requests to different ports running different
applications.

### nginx reverse proxy

Here is a minimal HTTP reverse proxy configuration:

    server {
        listen 80;                              # 80 is the default HTTP port
        server_name example.com;                # http://example.com/

        # Ensures that Gramex gets the real host, IP and protocol of the request
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Request-URI $request_uri;

        location /project/ {                    # example.com/project/* maps to
            proxy_pass http://127.0.0.1:9988/;  # 127.0.0.1:9988/
        }
    }

The use of the trailing slash makes a big difference in nginx.

    location /project/ { proxy_pass http://127.0.0.1:9988/; }   # Trailing slash
    location /project/ { proxy_pass http://127.0.0.1:9988; }    # No trailing slash

The first maps `example.com/project/*` to `http://127.0.0.1:9988/*`.
The second maps it to `http://127.0.0.1:9988/project/*`.

If you have Gramex running multiple applications under `/app1`, `/app2`, etc,
your config file will be like:

    location /app1/ { proxy_pass http://127.0.0.1:8001; }
    location /app2/ { proxy_pass http://127.0.0.1:8001; }
    location /app3/ { proxy_pass http://127.0.0.1:8001; }

But if your have a single app running at `/` in each Gramex instance root, your
config file will be like:

    location /app1/ { proxy_pass http://127.0.0.1:8001/; }
    location /app2/ { proxy_pass http://127.0.0.1:8002/; }
    location /app3/ { proxy_pass http://127.0.0.1:8003/; }

To let nginx cache responses, use:

    # Ensure /var/cache/nginx/ is owned by nginx:nginx with 700 permissions
    proxy_cache_path /var/cache/nginx/your-project-name
                     levels=1:2
                     keys_zone=your-project-name:100m
                     inactive=10d
                     max_size=2g;
    proxy_cache your-project-name;
    proxy_cache_key "$host$request_uri";
    proxy_cache_use_stale error timeout updating http_502 http_503 http_504;

To delete specific entries from the nginx cache, use
[nginx-cache-purge](https://github.com/perusio/nginx-cache-purge).

To allow websockets, add this configuration:

    # Allow nginx configuration upgrade
    proxy_http_version 1.1;
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host       $host;
    proxy_set_header X-Scheme   $scheme;

Additional notes:

- nginx allows files up to 1MB to be uploaded. You can increase that via
  [client_max_body_size](http://nginx.org/en/docs/http/ngx_http_core_module.html#client_max_body_size):
- If your response takes more than 60 seconds, use
  [proxy_read_timeout](http://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_read_timeout)
  to increase the timeout. (But speed up your application!)
- To pass the Gramex server version in the Server: HTTP header, use
  "[proxy_pass_header](http://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass_header) Server;"
- To enable HTTPS, read the Gramener wiki section on [SSL](https://learn.gramener.com/wiki/ssl.html)
