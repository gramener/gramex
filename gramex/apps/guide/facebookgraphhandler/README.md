---
title: FacebookGraphHandler
prefix: FacebookGraphHandler
...

[TOC]

[FacebookGraphHandler][facebookgraphhandler] offers a proxy for the [Facebook Graph API](https://developers.facebook.com/docs/graph-api/). Here is an example:

    :::yaml
    url:
        facebook:
            pattern: /facebook/(.*)
            handler: FacebookGraphHandler
            kwargs:
                # Visit https://developers.facebook.com/apps/ to get these keys
                key: '...'
                secret: '...'
            redirect:
                header: Referer
                url: /$YAMLURL/

Follow the steps for [Facebook auth](../auth/#facebook-auth) to get the keys above.

Now, follow these steps:

1. Click on [/facebook/me](facebook/me)
2. The first time you click on this, you get an "access token missing" error
3. So visit [/facebook/](facebook/) to log into Facebook
4. Now re-visit [/facebook/me](facebook/me)
5. This shows the logged-in user's profile in JSON

The request below will show your name once you log in. To log in, visit
[/facebook/](facebook/):

    :::js
    $.get('facebook/me')  // OUTPUT

After the OAuth login, users can be redirected via the `redirect:` config
documented the [redirection configuration](../config/#redirection).

The FacebookGraphHandler is very similar to the TwitterRESTHandler in many ways:

- You can use the `path:` configuration to hard-code a specific request. See the
  [Twitter paths](../twitterresthandler/#twitter-paths)
- You can use the `transform:` configuration to modify the response in any way.
  See the [Twitter transforms](../twitterresthandler/#twitter-transforms)
  documentation.
- See [Parallel AJAX requests](../twitterresthandler/#parellal-ajax-requests) to
  understand how to use these queries asynchronously.
- Instead of `POST`, you can use the `GET` method as well. See the documentation
  on [Twitter GET requests](../twitterresthandler/#twitter-get-requests)

See this [sample application](dashboard.html) and its [source][source] for examples of usage.

## Facebook Persist

If your app needs to persist the user's access token, add `access_token: persist`
to the kwargs. The first time, the user is asked to log in. Thereafter, the
user's credentials are available for all future requests.

This is typically used to show the latest posts / photos of a user or page on
every visit. Typically, such requests are cached as well. Here is a sample
configuration:

    :::yaml
    url:
      facebook-persist:
        pattern: /persist/(.*)
        handler: FacebookGraphHandler
        kwargs:
            key: '...'
            secret: '...'
            access_token: persist     # Persist the access token after first login
        cache:
            duration: 300             # Cache requests for 5 seconds

Here is a sample response:

    :::js
    $.get('persist/me')  // OUTPUT

The first time, you get an access_token error. Visit [/persist/](persist/) to log
in. Thereafter, your access_token will be stored and used for future requests
until it expires, or a user logs in again at [/persist/](persist/).

[source]: https://github.com/gramener/gramex/tree/dev/gramex/apps/guide/facebookgraphhandler/
[facebookgraphhandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.FacebookGraphHandler

<script>
function replace(e, regex, text) {
    e.innerHTML = e.innerHTML.replace(regex,
      '<p style="color: #ccc">// OUTPUT</p><p>' + text + '</p>')
}

var pre = [].slice.call(document.querySelectorAll('pre'))

function next() {
  var output_regex = /\/\/ OUTPUT/,
      element = pre.shift(),
      text = element.textContent

  if (text.match(output_regex))
    eval(text).always(function(result) {
      replace(element, output_regex, JSON.stringify(result, null, 2))
    })
  if (pre.length > 0) { next() }
}
next()
</script>
