title: Deployment patterns

Development and deployment are usually on different machines with different
configurations, file paths, database locations, etc. All of these can be
configured in `gramex.yaml` using pre-defined variables.

### Pre-defined variables

The following pre-defined variables are available in every YAML file:

- `$YAMLFILE`: absolute path to the current YAML file
- `$YAMLPATH`: absolute path to the current YAML file's directory
- `$YAMLURL`: relative path to the current YAML file's directory from the
  current working directory. For example, `base/dir/gramex.yaml` has a
  `$YAMLURL` of `base/dir`, and `gramex.yaml` has a `$YAMLURL` of `.`.
- `$GRAMEXPATH`: absolute path to the Gramex directory

For example, if you have the following directory structure:

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


## URLs

Your app may be running at `http://localhost:9988/` on your system, but will be
running at `http://server/app/` on the server. Use relative URLs and paths to
allow the application to work in both places.

Suppose `/gramex.yaml` imports all sub-directories:

    :::yaml
    import:
        apps: */gramex.yaml       # Import all gramex.yaml from 1st-level sub-directories

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
                        function: template            # Convert as a Tornado template
                        args: =content                # Using the contents of the file (default)
                        kwargs:                       # Pass it the following parameters
                            APP_ROOT: $APP_ROOT       # Pass the template the APP_ROOT variable

To test this, open the following URLs:

- [url/main](url/main)
- [url/main/sub](url/main/sub)
- [url/main/sub/third](url/main/sub/third)

In every case, the correct absolute path for `/style.css` is used,
irrespective of which path the app is deployed at.
