---
title: Deployment patterns
prefix: Deploy
...

[TOC]

Development and deployment are usually on different machines with different
configurations, file paths, database locations, etc. All of these can be
configured in `gramex.yaml` using pre-defined variables.

## Deployment checklist

- Check how to copy files to the server.
    - If copying into the server is allowed, use scp/rsync or Windows Remote
      Desktop copy/paste and transfer the codebase.
    - If not, check with IT team about code transfer mechanism.
- Set up Gramex.
    - If you don't have permission to install Gramex, request permissions from the IT team.
    - If Internet access is enabled, use the [default installation](https://learn.gramener.com/guide/install/)
    - If not, use the [offline install](https://learn.gramener.com/guide/install/#offline-install)
    - Run `gramex` (or) `python -m gramex`. This should load the Gramex documentation page.
- Set up the project.
    - Copy your project files.
    - Run Gramex from the project folder. This should load your project home page on the browser.
- Open required ports.
    - Access this application from a different system (e.g. `http://<serverip>:9988`).
      If it is not accessible, request the IT team to make the port accessible,
      or deploy on an accessible port.
    - If the application sends email, open the SMTP (25) / SMTPS (465/587) ports.
    - If the application uses LDAP, open the LDAP (389) / LDAPS (636) ports.
    - If the application uses HTTP to external sites, open the HTTP (80) / HTTPS (443) ports.
- Set up the domain.
    - Decide whether the app will be hosted on:
        - a new domain (e.g. `projectname.com`)
        - a new subdomain (e.g. `projectname.clientname.com`)
        - a new path (e.g. `clientname.com/projectname/`)
    - If a new domain / subdomain is required
        - If the client will manage this, raise a request with their IT team.
        - If Gramener will manage this, request <it@gramener.com>.
        - The domain name should point to the IP address of the server Gramex is deployed on.
    - If a new path is required, ask the client IT team to reverse proxy the
      path to the Gramex port. Read the [proxy servers](#proxy-servers) setup.
- Set up HTTPS.
    - If HTTPS is required, ensure that port `443` is open. Else raise a request with their IT team.
    - If the client will manage the SSL certificate, raise a request with their IT team.
      If Gramener will manage this, request <it@gramener.com> or get your own
      free certificate using [certbot](https://certbot.eff.org/).

## Windows Service

**v1.23**.
To install a Gramex application as a service on a Windows Server:

- [Install Anaconda and Gramex](../install/)
    - Download and install [Anaconda][anaconda] 4.4.0 or later
    - Run `pip install https://code.gramener.com/cto/gramex/repository/archive.tar.bz2?ref=master`.
      (Replace ``master`` with ``dev`` for the development version).
- Install your application in any folder - via `git clone` or by copying files
- Run PowerShell or the Command Prompt **as administrator**
- From your application folder, run `gramex service install`

This will start Gramex from the directory where you ran `gramex service install`
from. The next time the Gramex service starts, it will change to the directory
you are in. (Change this using `--cwd`)

Here are additional install options:

    gramex service install
        --cwd  "C:/path/to/application/"    # Run Gramex in this directory
        --user "DOMAIN\USER"                # Optional user to run as
        --password "user-password"          # Required if user is specified
        --startup manual|auto|disabled      # Default is manual

The user domain and name are stored as environment variables `USERDOMAIN` and
`USERNAME`. Run `echo %USERDOMAIN% %USERNAME%` on the Command Prompt to see them.

You can update these parameters any time via:

    gramex service update --...             # Same parameters as install

To uninstall the service, run:

    gramex service remove

To start / stop the application, go to Control Panel > Administrative Tools >
View Local Services and update your service. You can also do this from the
command prompt **as administrator**:

    gramex service start
    gramex service stop

Once started, the application is live at the port specified in your
`gramex.yaml`. The default port is 9988, so visit <http://localhost:9988/>. If no
`gramex.yaml` is found in the current directory, Gramex shows the Gramex Guide
(this application.)

Service logs can be viewed using the Windows Event Viewer. Gramex logs are at
`%LOCALAPPDATA%\Gramex Data\logs\` unless over-ridden by `gramex.yaml`.

To create multiple services running at different directories or ports, you can
create one or more custom service classes in `yourproject_service.py`:

```python
import gramex.winservice

class YourProjectGramexService(gramex.winservice.GramexService):
    _svc_name_ = 'YourServiceID'
    _svc_display_name_ = 'Your Service Display Name'
    _svc_description_ = 'Description of your service'
    _svc_port_ = 8123               # optional custom port

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(level=logging.INFO)
    YourProjectGramexService.setup(sys.argv[1:])
```

You can now run:

```bash
python yourproject_service.py install --cwd=...     # install the service
python yourproject_service.py remove                # uninstall the service
... etc ...
```

[anaconda]: http://continuum.io/downloads

### Windows administration

Here are some common Windows administration actions when deploying on Windows server:

- [Create a separate domain user to run Gramex](https://msdn.microsoft.com/en-in/library/aa545262(v=cs.70).aspx).
  Note: Domain users are different from [local users](https://msdn.microsoft.com/en-us/library/aa545420(v=cs.70).aspx)
- [Allow the domain user to log in via remote desktop](https://serverfault.com/a/483656/293853)
- [Give the user permission to run a service](https://support.microsoft.com/en-in/help/288129/how-to-grant-users-rights-to-manage-services-in-windows-2000)
  using [subinacl](http://go.microsoft.com/fwlink/?LinkId=23418).

### Windows scheduled tasks

To run a scheduled task on Windows, use PowerShell v3 ([ref](https://stackoverflow.com/a/8257779/100904)):

```bash
$dir = "D:\app-dir"
$name = "Scheduled-Task-Name"

Unregister-ScheduledTask -TaskName $name -TaskPath $dir -Confirm:$false -ErrorAction:SilentlyContinue
$action = New-ScheduledTaskAction –Execute "D:\anaconda\bin\python.exe" -Argument "$dir\script.py" -WorkingDirectory $dir
$trigger = New-ScheduledTaskTrigger -Daily -At "5:00am"
Register-ScheduledTask –TaskName $name -TaskPath $dir -Action $action –Trigger $trigger –User 'someuser' -Password 'somepassword'
```

An alternative for older versions of Windows / PowerShell is
[schtasks.exe](https://msdn.microsoft.com/en-us/library/windows/desktop/bb736357%28v=vs.85%29.aspx):

```bash
schtasks /create /tn your-task-name /sc HOURLY /tr "gramex"                # To run as current user
schtasks /create /tn your-task-name /sc HOURLY /tr "gramex" /ru SYSTEM     # To run as system user
```

## Linux service

There are 3 startup systems for Linux: System V (or sysvinit), Upstart and
systemd. Read this
[tutorial](https://www.digitalocean.com/community/tutorials/how-to-configure-a-linux-service-to-start-automatically-after-a-crash-or-reboot-part-1-practical-examples)
to set one up based on which is available in your system.

### Linux scheduled tasks

To run a scheduled task on Linux, use
[crontab](https://www.geeksforgeeks.org/crontab-in-linux-with-examples/)


## Security

To check for application vulnerabilities, run the [OWASP Zed Attack Proxy][zap].
It detects common vulnerabilities in web applications like cross-site scripting,
insecure cookies, etc.

Some common security options are pre-configured in `$GRAMEXPATH/deploy.yaml`. To
enable these options, add this line to your `gramex.yaml`:

```yaml
import: $GRAMEXPATH/deploy.yaml
```

This:

- **Disallows all files**, including code, config and data files like:
    - Code formats: `.py`, `.pyc`, `.php`, `.sh`, `.rb`, `.ipynb`, `.bat`, `.cmd`, `.bat`
    - Config formats: `.yml`, `.yaml`, `.ini`
    - Data formats: `.jsonl`, `.csv`, `.xlsx`, `.db`, `.xls`, `.h5`, `.xml`, `.shp`, `.shx`, `.dbf`, `.prj`, `.idx`, `.zip`, `.7z`
- Only allows content and front-end files, specifically:
    - Document formats: `.md`, `.markdown`, `.html`, `.txt`, `.pdf`,  `.rst`, `.pptx`, `.docx` (no `.doc`, `.ppt`, nor Excel files)
    - Image formats: `png`, `.svg`, `.jp*g`, `.gif`, `.ico`
    - Media formats: `.mp3`, `.mp4`, `.avi`, `.flv`, .`mkv`
    - Font formats: `.ttf`, `.woff*`, `.eot`, `.otf`
    - Front-end formats: `.js`, `.map`, `.vue`, `.less`, `.css` (not back-end formats like `.coffee`, `.scss`)
    - Front-end data format: `.json`
- enables `XSS` protection. Read more at [Mozilla Developer Docs](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-XSS-Protection).
- enables protection against browsers performing MIME-type sniffing. [Read more](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Content-Type-Options).
- enables protection against running apps within an iframe. [Read more](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Frame-Options).
- blocks server information. [Read more](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Server).

See [deploy.yaml][deploy-yaml] to understand the configurations.

[zap]: https://www.owasp.org/index.php/OWASP_Zed_Attack_Proxy_Project
[deploy-yaml]: https://code.gramener.com/cto/gramex/blob/master/gramex/deploy.yaml

## Relative URL mapping

Your app may be running at `http://localhost:9988/` on your system, but will be
running at `http://server/app/` on the server. Use relative URLs and paths to
allow the application to work in both places.

Suppose `/gramex.yaml` imports all sub-directories:

```yaml
import: */gramex.yaml   # Import all gramex.yaml from 1st-level sub-directories
```

... and `/app/gramex.yaml` has:

```yaml
url:
    page-name:
        pattern: /$YAMLURL/page         # Note the /$YAMLURL prefix
        handler: FileHandler
        kwargs:
            path: $YAMLPATH/page.html   # Note the $YAMLPATH prefix
```

When you run Gramex from `/app/`, the pattern becomes `/page` (`$YAMLURL` is `.`)

When you run Gramex from `/`, the pattern becomes `/app/page` (`$YAMLURL` is `/app`)

The correct file (`/app/page.html`) is rendered in both cases because
`$YAMLPATH` points to the absolute directory of the YAML file.

You can modify the app name using `../new-app-name`. For example, this pattern
directs the URL `/new-app-name/page` to `/app/page.html`.

```yaml
    pattern: /$YAMLURL/../new-app-name/page
```

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

```html
<link rel="stylesheet" href="/{{ APP_ROOT }}/style.css">
```

In `gramex.yaml`, we pass `APP_ROOT` to the that's set to `$YAMLURL`. For example:

```yaml
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
```

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

```yaml
url:
    relative-url:
        # This pattern: translates to /app/component/index.html
        # Note: leading slash (/) before $YAMLURL is REQUIRED
        pattern: /$YAMLURL/index.html
        handler: FileHandler
        kwargs:
            path: $YAMLPATH/        # This translates to /app/component/
```

If you want to refer to a file in the Gramex source directory, use
`$GRAMEXPATH`. For example, this maps [config](config) to Gramex's root
`gramex.yaml`.

```yaml
url:
    gramex-config-file:
        pattern: /$YAMLURL/config           # Map config under current URL
        handler: FileHandler
        kwargs:
            path: $GRAMEXPATH/gramex.yaml   # to the core Gramex config file
```

Typically, applications store data in `$GRAMEXDATA/data/<appname>/`. Create and use this directory for your data storage needs.


## HTTPS Server

To set up Gramex as a HTTPS server, you need a certificate file and a key file,
both in PEM format. Use the following settings in `gramex.yaml`:

```yaml
app:
    listen:
        port: 443
        ssl_options:
            certfile: "path/to/certificate.pem"
            keyfile: "path/to/privatekey.pem"
```

You can then connect to `https://your-gramex-server/`.

To generate a free HTTPS certificate for a domain, visit
[Certbot](https://certbot.eff.org/)

To generate a self-signed HTTPS certificate for testing, run:

```bash
openssl genrsa -out privatekey.pem 1024
openssl req -new -key privatekey.pem -out certrequest.csr
openssl x509 -req -in certrequest.csr -signkey privatekey.pem -out certificate.pem
```

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
            proxy_redirect ~^/ /project/;       # Redirects are sent back to /project/
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

    location /app1/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_redirect ~^/ /app1/;
    }
    location /app2/ {
        proxy_pass http://127.0.0.1:8002/;
        proxy_redirect ~^/ /app2/;
    }
    location /app3/ {
        proxy_pass http://127.0.0.1:8003/;
        proxy_redirect ~^/ /app3/;
    }

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


## Shared deployment

To deploy on Gramener's [UAT server](https://uat.gramener.com/monitor/apps), see
the [UAT deployment](https://learn.gramener.com/wiki/dev.html#deploying) section
and [deployment tips](https://learn.gramener.com/wiki/dev.html#deployment-tips).

This is a shared deployment, where multiple apps deployed on one Gramex
instance. Here are common deployment errors in shared environments:

### Works locally but not on server

If your app is at `D:/app/`, don't run gramex from `D:/app/`. Run it from `D:/`
with this `D:/gramex.yaml`:

```yaml
import: app/gramex.yaml
```

This tests the application in a shared deployment setup. The application may
run from `D:/app/` but fail from `D:/` - giving you a chance to find out why.

### 403 Forbidden

`$GRAMEXPATH/deploy.yaml` disables all non-standard files for
[security](#security). If another app imports `deploy.yaml`, your application
may not be able to access a file - e.g. `data.csv`. Create a FileHandler to
explicitly allow your file.

```yaml
url:
  myapp/allow-files:                        # Create/modify a handler to allow files
    pattern: /$YAMLURL/data/(.*)
    handler: FileHandler
    kwargs:
      path: $YAMLPATH/data/
      allow: ['data.csv', '*.xlsx']         # Explicitly allow required file types
```

**Do not use a custom `deploy.yaml`** in your project. Import from `$GRAMEXPATH`
instead. [Reference](#security). In case of a blanket disallow of files, refer
to 403 forbidden error above and resolve.

### 404 Not Found

Most often, this is due to relative paths. When running locally, the app
requests `/style.css`. But on the server, it is deployed at `/app/`. So the URL
must be `/app/style.css`. To avoid this, always use relative URLs - e.g.
`style.css`, `../style.css`, etc -- avoid the leading slash.

Another reason is incorrect [handler name conflicts](#handler-name-conflict).

### Handler name conflict

If your app and another app both use a URL handler called `data`, only one of
these will be loaded.

```yaml
url:            # THIS IS WRONG!
    data:       # This is defined by app1 -- only this config is loaded
        ...
    data:       # This is defined by app2 -- this is ignored with a warning in the log
        ...
```

Ensure that each project's URL handler is pre-fixed with a unique ID:

```yaml
url:            # THIS IS RIGHT
    app1/data:  # This is defined by app1
        ...
    app2/data:  # This is defined by app2 -- does not conflict with app1/data
        ...
```

### Import conflict

If your app and another app both `import:` the same YAML script, the namespaces
inside those will obviously collide:

```yaml
import:                                     # THIS IS WRONG!
    app1/ui:                                # app1
        path: $GRAMEXAPPS/ui/gramex.yaml    # imports UI components
        YAMLURL: $YAMLURL/app1/ui/          # at /app1/ui/
    app2/ui:                                # app2
        path: $GRAMEXAPPS/ui/gramex.yaml    # imports UI components
        YAMLURL: $YAMLURL/app2/ui/          # at /app2/ui/
```

Add the [namespace](#../config/#imports) key to avoid collision in specified
sections. A safe use is `namespace: [url, cache, schedule, watch]`

```yaml
import:                                     # THIS IS RIGHT
    app1/ui:                                # app1
        namespace: [url]                    # ensures that url: section names are unique
        path: $GRAMEXAPPS/ui/gramex.yaml
        YAMLURL: $YAMLURL/app1/ui/
    app2/ui:                                # app2
        namespace: [url]                    # ensures that url: section names are unique
        path: $GRAMEXAPPS/ui/gramex.yaml
        YAMLURL: $YAMLURL/app2/ui/
```

### Python file conflict

If your app and another app both use a Python file called `common.py`, only one
of these is imported. Prefix the Python files with a unique name, e.g.
`app1_common.py`.

### Missing dependency

Your app may depend on an external library -- e.g. a Python module, node module
or R library. Ensure that this is installed on the server. The preferred method
is to use the [gramex install](../install/) method. Specifically:

- Add Python modules to `requirements.txt`
- Add Node modules to `package.json`
- Add R libraries to `setup.sh` -- and ensure that the correct R is used
- Add any other custom code to `setup.sh`

### Log file order

Different instances of Gramex may flush their logs at different times. Do not
expect log files to be in order. For example, in this [request log](../config/#request-logging),
the 2nd entry has a timestamp greater than the third:

```
1519100063656,220.227.50.9,user1@masked.com,304,1,GET,/images/bookmark.png,
1519100063680,106.209.240.105,user2@masked.com,304,55,GET,/bookmark_settings?mode=display,
1519100063678,220.227.50.9,user3@masked.com,304,1,GET,/images/filters-toggler.png,
```
