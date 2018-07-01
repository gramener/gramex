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

## UploadHandler

[UploadHandler](../../uploadhandler/) now allows developer to specify store types. 
You define the `store` `type:` to store uploaded files metadata.
Earlier, only HDF5 store is allowed. But this has stability issues.
From `1.38` onwards `type:sqlite` is defaulted.
Older apps with `.meta.h5` will be migrated to `.meta.db`, incase the migration fails,
gramex will raise an exception and stop.

## Apache Load Balancing

Apart from documenting how to setup minimal
[nginx reverse proxy](../../deploy/#nginx-reverse-proxy) for Gramex apps,
Gramex guide also documents how to setup [Apache Load Balancing](../../deploy/#apache-load-balancing).

## Developer Updates

### g1
[`g1.js`](https://code.gramener.com/cto/g1) is upgraded to `0.8.2`
- g1 [$.urlfilter](https://code.gramener.com/cto/g1#urlfilter) works on forms,
inputs & sliders (not just links)
- g1 [$.formhandler()](https://code.gramener.com/cto/g1#formhandler) accepts
JavaScript data objects (instead of just a URL) as source

### Quickstart 
[quickstart tutorial](../../quickstart/) is now updated with FDD: Formhandler Driven Dashboard
approach, through a more generalized version of creating a dashboard/app in Gramex.

## Bug fixes

- gramex.cache `KeyStore` different stores stored keys differently, This caused unicode keys to be
stored inconsistently. This is now fixed.
[#442](https://code.gramener.com/cto/gramex/issues/442)

- FormHandler query request `?col=` as NOT-NULL for int/float rows used to fail. This is now plugged.
[#432](https://code.gramener.com/cto/gramex/issues/432)

## Stats

- Code base: 26,394 lines (python: 16,077, javascript: 1,518, tests: 8,799)
- Test coverage: xx%

## Upgrade

To upgrade Gramex, run:

```bash
pip install --verbose gramex==1.38
```

This downloads Chromium and other front-end dependencies. That may take time.
