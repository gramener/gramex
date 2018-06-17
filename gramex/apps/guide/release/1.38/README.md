---
title: Gramex 1.38 Release Notes
prefix: 1.38
...

[TOC]

## EmailAuth

[EmailAuth](../../auth/#emailauth) allows any user with a valid email ID to log
in. This is a convenient alternative to [DBAuth](../../auth/#dbauth). Users do
not need to sign-up. Administrators don't need to provision accounts. Gramex can
[restrict access](../../auth/#authorization) based on just their email ID or
domain.

For example, to allow all users from @ibm.com or @pwc.com, use:

```yaml
url:
  login:
    pattern: /$YAMLURL/login
    handler: EmailAuth
    kwargs:
      service: email-service
      subject: 'OTP for <app name>'
      body: 'The OTP for {user} is {password}. Visit {link}'
  dashboard:
    ...
    kwargs:
      auth:
        membership:
          - {hd: [ibm.com, pwc.com]}
          - {email: [admin@example.org]}
```


## Bug fixes


## Stats

- Code base: xx,xxx lines (python: xx,xxx, javascript: x,xxx, tests: x,xxx)
- Test coverage: xx%

## Upgrade

To upgrade Gramex, run:

```bash
pip install --verbose gramex==1.38
```

This downloads Chromium and other front-end dependencies. That may take time.
