---
title: Admin page
prefix: Admin
...

[TOC]

## Admin page

From v1.42, Gramex ships with an admin page. To include it in your page, use:

```yaml
import:
  admin/admin:
    path: $GRAMEXAPPS/admin2/gramex.yaml    # Note the "admin2" instead of "admin"
    YAMLURL: /$YAMLURL/admin/               # URL to show the admin page at
```

<div class="example">
  <a class="example-demo" href="admin/">Admin page example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/admin/gramex.yaml">Source</a>
</div>

You can configure the admin page as follows:

```yaml
import:
  admin/admin-kwargs:
    path: $GRAMEXAPPS/admin2/gramex.yaml
    YAMLURL: /$YAMLURL/admin-kwargs/        # URL to show the admin page at
    ADMIN_KWARGS:
      logo: https://gramener.com/uistatic/gramener.png  # Logo URL
      home: /$YAMLURL/                                  # URL that logo links to
      title: Admin  Page Options                        # Navbar title
      components: [info, users, shell]                  # Components to show
      theme: '?font-family-base=roboto'                 # UI component theme query
    ADMIN_AUTH:
      membership:
        email: [admin1@example.org, admin2@example.org]     # Only allow these users
```

The `ADMIN_KWARGS` section accepts the following parameters:

- `logo`: Logo image URL. Either an absolute URL or relative to the admin page.
- `home`: Logo link URL. Clicking on the logo takes you to this link.
- `title`: Title displayed on the navbar. Defaults to "Admin"
- `theme`: The [UI theme](../uicomponents/) for the page. For example,
  `?font-family-base=Roboto` makes the font Roboto.
- `components`: List of components to display. The admin page has pre-defined
  components (documented below). By default, all components are displayed. The list of components are:
    - `user`: [User management component](#admin-user-management)
    - `schedule`: [Schedule component](#admin-schedule)
    - `shell`: [Python web shell component](#admin-shell)
    - `info`: [Gramex & server info component](#admin-info)
    - `config`: [Gramex configuration component](#admin-config)
    - `logs`: [Log viewer component](#admin-logs)

The `ADMIN_AUTH` section is the same as specifying the `auth:`
[authorization](../auth/#authorization) on all admin pages.

<div class="example">
  <a class="example-demo" href="admin-kwargs/">Admin page options example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/admin/gramex.yaml">Source</a>
</div>

## Admin: User management

To manage users, add roles and other attributes, use the `user` component.
To enable it:

1. Ensure that `users` is in `components:` (e.g. `components: [users, ...]`) or
   you don't specify any components.
2. Add an `authhandler:` that has the name of a [auth handler](../auth/) that is
   either a [DBAuth](../auth/#dbauth) or has a [lookup section](../authhandler/#lookup-attributes)

For example:

```yaml
import:
  admin/admin-user:
    path: $GRAMEXAPPS/admin2/gramex.yaml
    YAMLURL: /$YAMLURL/admin-user/
    ADMIN_KWARGS:
      authhandler: login        # Manages users via the url: key named "login"

url:
  login:                        # Here is the url: key named "login"
    pattern: ...
    handler: DBAuth             # This must either be DBAuth...
    kwargs:
      ...
      lookup:                   # ... or have a lookup: section
        ...
```

<div class="example">
  <a class="example-demo" href="admin-user/">User management example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/admin/gramex.yaml">Source</a>
</div>

User management is available as a component. To embed it in your page, add a
FormHandler table component:

```html
<div class="users"></div>
<script>
  $('.users').formhandler({
    src: 'admin/users-data',    // Assuming the admin page is at admin/
    edit: true,                 // Allow editing users
    add: true                   // Allow adding users
  })
</script>
```

<div class="example">
  <a class="example-demo" href="users.html">User management component example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/admin/users.html">Source</a>
</div>

You can specify custom actions & formats using FormHandler table. See the [admin page source code](https://github.com/gramener/gramex/blob/dev/gramex/apps/admin2/index.html) for examples of custom actions.

## Admin: Schedule

The schedule component lets you see all [scheduler tasks](../scheduler/) defined
under the `schedule:` section, and run them.

<div class="example">
  <a class="example-demo" href="admin/schedule">Schedule example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/admin/">Source</a>
</div>

The admin schedule component can be embdded in any page:

```html
<div class="schedule"></div>
<script src="schedule.js"></script>
<script>
  $('.schedule').schedule({           // Embed the scheduler
    url: 'admin/schedule-data',       // Assuming the admin page is at admin/
    xsrf: '{{ handler.xsrf_token }}'  // Pass XSRF token. Requires FileHandler template
  })
</script>
```

<div class="example">
  <a class="example-demo" href="schedule.html">Schedule component example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/admin/schedule.html">Source</a>
</div>

## Admin: Alerts

The alert component lets you see all [alerts](../alert/) defined under the
`alert:` section, and preview or run them.

<div class="example">
  <a class="example-demo" href="admin/alert">Alert example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/admin/">Source</a>
</div>

The admin alert component can be embdded in any page:

```html
<div class="schedule"></div>
<script src="schedule.js"></script>
<script>
  $('.schedule').schedule({           // Alerts use the same component as schedulers
    alert: true,                      // ... but with the alert: true option
    url: 'admin/alert-data',          // Assuming the admin page is at admin/
    xsrf: '{{ handler.xsrf_token }}'  // Pass XSRF token. Requires FileHandler template
  })
</script>
```

## Admin: Shell

The shell adds a web-based Python shell that runs commands within the running
Gramex instance. This is useful when debugging a live environment.
To enable it, ensure that you specify:

- Either `components: [..., shell, ...]`, i.e. include `shell` in `components:`
- Or do not specify any `components:`

In the shell, you can run these commands:

```python
1 + 2                   # Evaluate Python expressions
import gramex           # All gramex libraries are available
handler.session         # WebsocketHandler instance is available as 'handler'
```

The web shell is available as a component. To embed it in your page, add:

```html
<div class="webshell"></div>
<script src="admin/webshell.js"></script>
<script>
  $('.webshell').webshell({           // Embed the web shell here
    url: 'admin/webshell-data',       // Assuming the admin page is at admin/
    prompt: '>>> ',                   // Prompt to display at the start of each page
    welcome: [                        // Welcome message as a list of lines.
      'Welcome to the Gramex shell',
      '>>> '
    ]
  })
</script>
```

<div class="example">
  <a class="example-demo" href="shell.html">Web shell component example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/admin/shell.html">Source</a>
</div>

## Admin: Info

The info page shows information about versions, paths and other details about
Gramex and its dependencies.

To enable it, ensure that you specify:

- Either `components: [..., info, ...]`, i.e. include `info` in `components:`
- Or do not specify any `components:`

This exposes JSON data at `<admin-page>/info-data` as a list of objects
consistent with [FormHandler](../formhandler/).

```json
[
    {"section":"git","key":"path","value":"D:\\bin\\git.EXE","error":null},
    {"section":"git","key":"version","value":"git version 2.15.1\n","error":""},{"section":"gramex","key":"memory usage","value":153411584,"error":""},
    ...
]
```

The information provided includes (in a `<section>.<key>` notation):

- `git.path`: path where git is installed
- `git.version`: git version
- `node.path`: path where node is installed
- `node.version`: node version
- `npm.version`: npm version
- `yarn.version`: yarn version
- `python.path`: path where Python is installed
- `python.version`: Python version
- `gramex.path`: path where this instance of Gramex is installed
- `gramex.version`: Gramex version (for current instance)
- `gramex.memory-usage`: total memory used by Gramex
- `gramex.open-files`: number of files opened by Gramex
- `system.cpu-count`: number of CPUs in the system
- `system.cpu-usage`: % of CPU used by the system
- `system.disk-usage`: % of root disk used by the system
- `system.memory-usage`: % of memory used by the system

The result is stored in the `value` column. If the value is not available, the `error` is stored in the `error` column.

<div class="example">
  <a class="example-demo" href="admin-kwargs/?tab=info">Info page example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/admin/gramex.yaml">Source</a>
</div>


## Admin: Config

WIP: Shows the Gramex configuration, and allows users to edit it.

## Admin: Logs

WIP: Shows the Gramex logs.


## Admin access control

TODO: explain how to restrict admin access


## Admin page (old)

From v1.33, Gramex used a beta version of the admin page. This is **deprecated**.

To use it, add this to your `gramex.yaml`:

```yaml
import:
  admin1:
    path: $GRAMEXAPPS/admin/gramex.yaml   # Source of the app
    YAMLURL: /$YAMLURL/admin1/       # Location to mount at
    ADMIN_LOOKUP:
      url: $YAMLPATH/lookup.xlsx          # DB / file with user information
      id: user                            # Column name that has the user ID
```

<div class="example">
  <a class="example-demo" href="admin1/">Admin page (old)</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/admin/gramex.yaml">Source</a>
</div>

Use `ADMIN_*` variables to configure your app.

- `ADMIN_LOOKUP`: See [lookup attributes]../auth/#lookup-attributes):
  - `url`: the DB or file that has user data
  - `id`: column that has the user ID
- `ADMIN_KWARGS`:
  - `hide`: columns in data source to exclude (like password and other sensitive data)
- `ADMIN_USER`: optional `string` or `list` of user IDs that can view this admin page
- `ADMIN_ROLE`: optional `string` or `list` of roles. If the user's `role` column is in this list, the user can view this admin page
- `LOGIN_URL`: Login url for admin page. Incase of DBAuth, this will be same as pattern for DBAuth handler
- `LOGOUT_URL`: The url pattern provided for `LogoutHandler`

Sample use of `role`:

```yaml
import:
  admin:
    path: $GRAMEXAPPS/admin/gramex.yaml
    YAMLURL: /$YAMLURL/admin/
    ADMIN_LOOKUP:
      url: $YAMLPATH/lookup.xlsx
      id: user                   # user column in Excel sheet has the user name
    ADMIN_USER: ['alpha']        # Always allow user `alpha`
    ADMIN_ROLE: ['admin']        # Also allow anyone with role as admin
    LOGIN_URL: /admin/           # URL to show login page for admin page
    LOGOUT_URL: /logout/         # URL to logout
```

By default, admin site can be accessed by any user when using `127.0.0.1`.
