---
title: ProxyHandler proxies APIs
prefix: ProxyHandler
...

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

This configuration proxies the Google APIs at `googleapis.com`:

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

### Google Services

<div class="example">
  <a class="example-demo" href="../auth/google">Log into Google</a>
  <a class="example-src" href="http://github.com/gramener/gramex/tree/master/gramex/apps/guide/auth/">Source</a>
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
- Access the [Contacts API](https://developers.google.com/google-apps/contacts/v3/)
  using `https://www.google.com/m8/feeds/contacts/` as the endpoint
    - [Contacts updated since 2018](googlecontacts/default/full?updated-min=2018-01-01T00:00:00)
- Access the [Natural Language API](https://cloud.google.com/natural-language/docs/)
    - [v1 API discovery](googlelanguage/$discovery/rest?version=v1)


### Google Translate

**Note**: Use the [Gramex translate](../translate/) functionality to cache & edit translations.

You can set up a secret key to access the
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

### Google Search

To access the
[Google Custom Search API](https://developers.google.com/custom-search/json-api/v1/overview)
set up a custom search engine that [searches the entire web](https://stackoverflow.com/a/11206266/100904).
Then with an API key,
use the [REST API](https://developers.google.com/custom-search/json-api/v1/using_rest)
and [reference](https://developers.google.com/custom-search/json-api/v1/reference/cse/list),
fetch search results.

```yaml
    proxyhandler/googlesearch:
        pattern: /$YAMLURL/googlesearch
        handler: ProxyHandler
        kwargs:
          url: https://www.googleapis.com/customsearch/v1
          default:
            key: ...        # Your API key
            cx: ...         # Your custom search engine ID
```

Here are some examples of searches:

- [Gramener mentions last week when searching from the US](googlesearch?q=gramener&dateRestrict=1w&gl=us)
- [Pages related to gramener.com](googlesearch?relatedSite=gramener.com&q=)
[Google Translate API](https://cloud.google.com/translate/docs/quickstart):

### Google Cloud NLP

You can also analyze text using [NLP](https://cloud.google.com/natural-language/docs/):

```yaml
    proxyhandler/googlelanguage:
        pattern: /$YAMLURL/googlelanguage/(.*)
        handler: ProxyHandler
        kwargs:
            url: https://language.googleapis.com/{0}
            method: POST
            request_headers:
              "*": true
            default:
              key: ...
```

Sending a POST request to `googlelanguage/v1/documents:analyzeEntities` with
this JSON content analyzes the entities:

```js
{
    "document": {
        "type": "PLAIN_TEXT",
        "language": "en",
        "content": "The Taj Mahal is in Agra"
    },
    "encodingType": "UTF8"
}
```

<button class="post-button" data-href="googlelanguage/v1/documents:analyzeEntities" data-target="#entity-result" data-body='{
    "document": {
        "type": "PLAIN_TEXT",
        "language": "en",
        "content": "The Taj Mahal is in Agra"
    },
    "encodingType": "UTF8"}'>Analyze the entities</button>

<div class="codehilite"><pre>Click the button above to see the result</pre></div>


To analyze the sentiment of text, send a POST request to
`googlelanguage/v1/documents:analyzeSentiment` with this JSON content:

```javascript
{
    "document": {
        "type": "PLAIN_TEXT",
        "language": "en",
        "content": "Disliking watercraft is not really my thing"
    },
    "encodingType": "UTF8"
}
```

<button class="post-button" data-href="googlelanguage/v1/documents:analyzeSentiment" data-target="#sentiment-result" data-body='{
    "document": {
        "type": "PLAIN_TEXT",
        "language": "en",
        "content": "Disliking watercraft is not really my thing"
    },
    "encodingType": "UTF8"}'>Analyze the sentiment</button>

<div class="codehilite"><pre>Click the button above to see the result</pre></div>


## Facebook ProxyHandler

This configuration proxies the Facebook Graph API at `graph.facebook.com`:

```yaml
url:
    proxyhandler/facebook:
        pattern: /$YAMLURL/facebook/(.*)
        handler: ProxyHandler
        kwargs:
            url: https://graph.facebook.com/{0}
            default:
                access_token: '{handler.session[user][access_token]}'
```

To access the Facebook APIs, set up a [Facebook Auth handler](../auth/#facebook-auth).

<div class="example">
  <a class="example-demo" href="../auth/facebook">Log into Facebook</a>
  <a class="example-src" href="http://github.com/gramener/gramex/tree/master/gramex/apps/guide/auth/">Source</a>
</div>

Once logged in, you can:

- [Access your profile](facebook/me)
- [Access your feed](facebook/me/feed)
- [Access your friends](facebook/me/friends)
- [Access your photos](facebook/me/photos)


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


<script src="proxyhandler.js?v=16"></script>

[proxyhandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.ProxyHandler
[xsrf]: ../filehandler/#xsrf
[httprequest]: http://www.tornadoweb.org/en/stable/httpclient.html#tornado.httpclient.HTTPRequest
[httpresponse]: http://www.tornadoweb.org/en/stable/httpclient.html#tornado.httpclient.HTTPResponse
