---
title: Windows IntegratedAuth
prefix: Tip
...

[Gramex 1.22](https://learn.gramener.com/gramex/history.html#id2) has a new authentication mechanism called
[IntegratedAuth](../auth/#integrated-auth). This lets Windows users automatically
log in without having to type their ID or password.

This can be set up instead of `LDAPAuth`. Wherever you use `LDAPAuth` (e.g. Axis,
ICICI) or where the the system is running on Windows (e.g. Star, Times, maybe
GroupM and Novartis), we can use this.

The setup is very simple:

    :::yaml
    auth/login:
        pattern: /$YAMLURL/login
        handler: IntegratedAuth

When the user visits `/login`, it will automatically log the user in. The `handler.current_user` object looks like this:

    :::js
    {
        "id": "EC2-175-41-170-\\Administrator", // same as domain\username
        "domain": "EC2-175-41-170-",            // Windows domain name
        "username": "Administrator",            // Windows user name
        "realm": "WIN-8S90I248M00"              // Windows hostname
    }

This MAY ASK for a username and password. If so, users can enter their Windows ID and password.

To prevent asking, enable SSO on
[IE/Chrome](https://docs.aws.amazon.com/directoryservice/latest/admin-guide/ie_sso.html) or on
[Firefox](https://wiki.shibboleth.net/confluence/display/SHIB2/Single+sign-on+Browser+configuration).
It's a set up that needs to be done either by their administrator or all end users.
