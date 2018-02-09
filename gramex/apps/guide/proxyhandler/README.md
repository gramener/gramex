title: Gramex proxies HTTP requests

[TOC]

[ProxyHandler][proxyhandler] passes requests to another URL and returns its
response. Here are some reasons to use it:

- Github provides a REST API, but this cannot be accessed from the browser.
  ProxyHandler mirrors the Github API for use from the browser
- Google, Facebook, etc provide a REST API that require authentication.
  ProxyHandler lets users logged into Gramex use these APIs from the browser
  without needing to pass an API key. The API key is part of the application
- We have an R-Shiny app that is open to all. We want only users of the Gramex
  application to access it. ProxyHandler proxies the app and allows only
  authenticated users to access it.

For example:

```yaml
url:
    proxyhandler/github:
        pattern: /$YAMLURL/github/(.*)          # Send all requests for github/
        handler: ProxyHandler
        kwargs:
            url: https://api.github.com/{0}     # {0} is replaced with what's in (.*)
            request_headers:
                User-Agent: true                # also send the user's browser info
```

This forwards [github/search/users](github/search/users) to `https://api.github.com/search/users`. For example:

- [github/users/gramener](github/users/gramener) gets the Gramener org profile
- [github/search/users?q=language:python&sort=followers](github/search/users?q=language:python&sort=followers) shows the top Python developers
- [github/search/repositories?q=language:javascript&sort=stars](github/search/repositories?q=language:javascript&sort=stars) shows the most starred JS repos

For more operators see the [Github API](https://developer.github.com/v3/)

## ProxyHandler Configuration

ProxyHandler configuration accepts these kwargs:

- `url`: URL endpoint to forward to. All captured groups in the `pattern:`
  regular expression like `/(group|item)/(.*)` can be used in the url as `{0}`,
  `{1}`, etc. The first item `(group|item)` becomes `{0}`. The second is `{1}`.
- `request_headers`: dict of HTTP headers to be passed to the url.
    - A value of `true` forwards this header from the request as-is. For example:
        - `User-Agent: true` passes the User-Agent header as-is
        - `Cookie: true` passes the HTTP cookie header as-is
    - Any value is string-formatted with `handler` as a variable. For example:
      `Authorization: 'Bearer {handler.session[google_access_token]}'` will
      use the `google_access_token` key from the session.
    - `"*": true` all HTTP headers from the request as-is
- `default`: dict of default URL query parameters. For example, `alt: json` will
  add a `?alt=json` to all requests by default. Over-ride this by requesting
  `?alt=something-else` explicitly.
- `headers`: dict of HTTP headers to set on the response
- `methods`: list of HTTP methods allowed. Defaults to `GET`, `HEAD` and `POST`.
  Remember that `POST` and other write methods require [XSRF][xsrf] -- either a
  `?_xsrf=` argument or a `X-Xsrftoken` HTTP header.
- `prepare`: a function that accepts any of `handler` and `request` (a
  [HTTPRequest][httprequest]) and modifies the `request` in-place
- `modify`: a function that accepts any of `handler`, `request` (a
  [HTTPRequest][httprequest]), and `response` (a [HTTPResponse][httpresponse])
  and modifies the `response` in-place
- `connect_timeout`: timeout for initial connection in seconds (default: 20)
- `request_timeout`: timeout for entire request in seconds (default: 20)

All [standard handler kwargs](../handler/) like `auth:`, `cache:`,
`xsrf_cookies`, `error:`, etc. are also available.


## Google ProxyHandler

This configuration proxies the Google at `googleapis.com`:

```yaml
url:
    proxyhandler/google:
        pattern: /$YAMLURL/google/(.*)
        handler: ProxyHandler
        kwargs:
            url: https://www.googleapis.com/{0}
            request_headers:
                Authorization: 'Bearer {handler.session[google_access_token]}'
```

To access the Google APIs, set up a [Google Auth handler](../auth/#google-auth).
To get permission from the user for specific apps, add a `scopes:` section that
lists the permissions you need. Here is the
[full list of scopes](https://developers.google.com/identity/protocols/googlescopes).

<div class="example">
  <a class="example-demo" href="../auth/google">Log into Google</a>
  <a class="example-src" href="http://code.gramener.com/s.anand/gramex/tree/master/gramex/apps/guide/auth/">Source</a>
</div>

Once logged in, you can:

- Access the [GMail API](https://developers.google.com/gmail/api/v1/reference/)
    - [Profile](https://developers.google.com/gmail/api/v1/reference/users/getProfile):
      [google/gmail/v1/users/me/profile](google/gmail/v1/users/me/profile)
    - [Messages list](https://developers.google.com/gmail/api/v1/reference/users/messages/list):
      [google/gmail/v1/users/me/messages](google/gmail/v1/users/me/messages)
    - [Filters list](https://developers.google.com/gmail/api/v1/reference/users/settings/filters/list)
      [google/gmail/v1/users/me/settings/filters](google/gmail/v1/users/me/settings/filters)
- Access the [Calendar API](https://developers.google.com/google-apps/calendar/v3/reference/)
    - [Calendar list](https://developers.google.com/google-apps/calendar/v3/reference/calendarList/list):
      [google/calendar/v3/users/me/calendarList](google/calendar/v3/users/me/calendarList)
    - [Primary calendar event list](https://developers.google.com/google-apps/calendar/v3/reference/events/list):
      [google/calendar/v3/calendars/primary/events](google/calendar/v3/calendars/primary/events?maxResults=10)
    - [Calendar settings](https://developers.google.com/google-apps/calendar/v3/reference/settings/list):
      [google/calendar/v3/users/me/settings](google/calendar/v3/users/me/settings)
- Access the [Drive API](https://developers.google.com/drive/v3/reference/)
    - [Drive info](https://developers.google.com/drive/v3/reference/about/get)
      [google/drive/v3/about](google/drive/v3/about?fields=*)
    - [List files](https://developers.google.com/drive/v3/reference/files/list):
      [google/drive/v3/files](google/drive/v3/files)
    - [List teamdrives](https://developers.google.com/drive/v3/reference/teamdrives/list):
      [google/drive/v3/files](google/drive/v3/teamdrives)

You can also set up a secret key and access the
[Google Translate API](https://cloud.google.com/translate/docs/quickstart):

```yaml
    proxyhandler/googletranslate:
        pattern: /$YAMLURL/googletranslate
        handler: ProxyHandler
        kwargs:
            url: https://translation.googleapis.com/language/translate/v2
            default:
              # Get key from https://cloud.google.com/translate/docs/quickstart
              key: ...
```

Now you can translate across [languages](https://cloud.google.com/translate/docs/languages):

- [How are you in German](googletranslate?q=How+are+you&target=de)
- [How are you from German to Hindi](googletranslate?q=Wie+geht+es+Ihnen&target=hi)


## Reverse ProxyHandler

This configuration mirrors <https://gramener.com/demo/> at [demo/](demo/), but
only allows authenticated users.

```yaml
url:
    proxyhandler/gramener.com:
        pattern: /$YAMLURL/(demo|uistatic|node_modules|bowerlib)/(.*)
        handler: ProxyHandler
        kwargs:
            url: https://gramener.com/{0}/{1}
            auth: true
        cache:
            expiry: {duration: 300}
```

All requests to the URLs demo, uistatic, node_modules, bowerlib are redirected
to `gramener.com/` - but only if the user is logged in. This lets us expose
internal applications to users who are logged in via Gramex.

Further, it caches the response for 300s (5 min) -- making this an authenticated
caching reverse proxy.


[proxyhandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.ProxyHandler
[xsrf]: ../filehandler/#xsrf
[httprequest]: http://www.tornadoweb.org/en/stable/httpclient.html#tornado.httpclient.HTTPRequest
[httpresponse]: http://www.tornadoweb.org/en/stable/httpclient.html#tornado.httpclient.HTTPResponse
