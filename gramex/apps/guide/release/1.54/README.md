---
title: Gramex 1.54 release notes
prefix: 1.54
...

[TOC]

## Admin components URL changed

**This is a breaking change**. If you use the [admin page](../../admin/) with
*components* using JavaScript, the URLs have changed. You should:

- Replace `admin/users` with `admin/users-data`
- Replace `admin/webshell` with `admin/webshell-data`
- Replace `admin/info` with `admin/info-data`

For example:

```js
  // This works before 1.54, but NOT from 1.54
  $('.users').formhandler({ src: 'admin/users' })
  // Replace it with:
  $('.users').formhandler({ src: 'admin/users-data' })
```
