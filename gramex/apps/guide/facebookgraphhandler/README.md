title: Gramex accesses Facebook data

`FacebookGraphHandler` offers a proxy for the [Facebook Graph API](https://developers.facebook.com/docs/graph-api/). Here is an example:

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


[source]: https://code.gramener.com/s.anand/gramex/tree/dev/gramex/apps/guide/facebookgraphhandler


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
