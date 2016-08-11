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
                access_token: '...'

Follow the steps for [Facebook auth](../auth/#facebook-auth) to get the keys above.

Now, `POST /facebook/me` will show your user information. It's the same as `GET
https://graph.facebook.com/me`, but pre-authenticated with the keys provided in
`kwargs`.

To use just a specific REST API, use the `path:` parameter. For example:

    :::yaml
    url:
        facebook/myphotos:
            pattern: /facebook/myphotos       # Maps this URL
            handler: FacebookGraphHandler
            kwargs:
                path: /me/photos              # specifically to this API call
                ...

... maps `/facebook/myphotos` to `https://graph.facebook.com/me/photos` with the
relevant authentication.

The examples below use [jQuery.ajax][jquery-ajax] and the [cookie.js][cookie.js] libraries.

[jquery-ajax]: http://api.jquery.com/jquery.ajax/
[cookie.js]: https://github.com/florian/cookie.js

<script src="https://cdnjs.cloudflare.com/ajax/libs/cookie.js/1.2.0/cookie.min.js"></script>

## Facebook OAuth

The above examples allowed you to query Facebook with a pre-defined access
token. But for users to use their own account to access the API, **do not
specify an `access_token`. It will redirect the user to Facebook and log them
in.

For example, the first time you make a POST request to `oauth-api/` (see output
below), you will see an error message saying `access token missing`. But visit
[oauth-api/?next=../](oauth-api/?next=../) and log into Facebook. Then visit this
page. The request below will show your name.

    :::js
    var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
    $.ajax('oauth-api/me', {
      headers: xsrf,
      method: 'POST',
    })  // OUTPUT


Additional documentation:

- You can use the `transform:` configuration to modify the response in any way.
  See the [Twitter transforms](../twitterresthandler/#twitter-transforms)
  documentation.
- See [Parallel AJAX requests](../twitterresthandler/#parellal-ajax-requests) to
  understand how to use these queries asynchronously.
- Instead of `POST`, you can use the `GET` method as well. See the documentation
  on [Twitter GET requests](../twitterresthandler/#twitter-get-requests)


<script>
var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
var pre = [].slice.call(document.querySelectorAll('pre'))

function replace(e, regex, text) {
    e.innerHTML = e.innerHTML.replace(regex, 
      '<p style="color: #ccc">// OUTPUT</p><p>' + text + '</p>')
}

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
