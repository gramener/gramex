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

## FormHandler Group By

[FormHandler](../../formhandler/#formhandler-groupby) supports grouping by
columns and custom aggregations. For example:
[?_by=Continent&_c=Name|count&_c=c1|min&_c=c1|avg&_c=c1|max](../../formhandler/flags?_by=Continent&_c=Name|count&_c=c1|min&_c=c1|avg&_c=c1|max&_format=table) does:

- `_by=Continent`: group by "Continent"
- `_c=Name|count`: count values in "Name"
- `_c=c1|min`: min value of "c1" in each continent
- `_c=c1|avg`: mean value of "c1" in each continent
- `_c=c1|max`: max value of "c1" in each continent

This should eliminate the need to write custom queries for most simple scenarios.

## Developer Updates

g1 is upgraded to `0.8.2`

- g1 [$.urlfilter](https://code.gramener.com/cto/g1#urlfilter) works on forms,
inputs & sliders (not just links)
- g1 [$.formhandler()](https://code.gramener.com/cto/g1#formhandler) accepts
JavaScript data objects (instead of just a URL) as source

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
