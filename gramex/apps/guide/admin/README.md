---
title: Admin page
prefix: Admin
...

[TOC]

From v1.33, Gramex ships with a admin site. Admin site is currently in beta state.

To use it, add this to your `gramex.yaml`:

```yaml
import:
  admin:
    path: $GRAMEXAPPS/admin/gramex.yaml   # Source of the app
    YAMLURL: $YAMLURL/admin/              # Location to mount at
    ADMIN_LOOKUP:
      url: $YAMLURL/lookup.xlsx           # DB / file with user information
      id: user                            # Column name that has the user ID
```

<div class="example">
  <a class="example-demo" href="admin/">Admin page</a>
  <a class="example-src" href="http://code.gramener.com/cto/gramex/tree/master/gramex/apps/guide/admin/gramex.yaml">Source</a>
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
    YAMLURL: $YAMLURL/admin/
    ADMIN_LOOKUP:
      url: $YAMLURL/lookup.xlsx
      id: user                   # user column in Excel sheet has the user name
    ADMIN_USER: ['alpha']        # Always allow user `alpha`
    ADMIN_ROLE: ['admin']        # Also allow anyone with role as admin
    LOGIN_URL: /admin            # Url to show login page for admin page 
    LOGOUT_URL: /logout          # Url to logout
```

By default, admin site can be accessed by any user when using `127.0.0.1`.
