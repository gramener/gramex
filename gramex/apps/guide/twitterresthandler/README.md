title: Gramex accesses Twitter data

`TwitterRESTHandler` offers a proxy for the [Twitter 1.1 REST API](https://dev.twitter.com/rest/public), with the added advantage of being asynchronous.

Here is a sample usage:

    :::yaml
    url:
        twitter:
            pattern: '/twitter/(.*)'
            handler: TwitterRESTHandler
            kwargs:
                consumer_key: '...'
                consumer_secret: '...'
                access_token: '...'
                access_token_secret: '...'
                methods: [GET, POST]          # Allow GET / POST requests to this endpoint

Follow the steps for [Twitter auth](../auth/#twitter-auth) to get the keys above.

Now, `POST /twitter/search/tweets.json?q=beer` will return tweets about beer.
Reference: [GET search/tweets](search-tweets).
It's the same as `GET https://api.twitter.com/1.1/search/tweets.json?q=beer`,
but without the need for authentication.

The `methods:` parameter specifies which methods to use to access the API. The
default is just `POST`. You can replace it with `[GET, POST]` to use either
GET or POST, or `GET` to use only the `GET` HTTP method.

The examples below use [jQuery.ajax][jquery-ajax] and the [cookie.js][cookie.js] libraries.

[jquery-ajax]: http://api.jquery.com/jquery.ajax/
[cookie.js]: https://github.com/florian/cookie.js
[search-tweets]: https://dev.twitter.com/rest/reference/get/search/tweets

<script src="https://cdnjs.cloudflare.com/ajax/libs/cookie.js/1.2.0/cookie.min.js"></script>

## Twitter search

The following request fetches the latest Tweet for Gramener:

    :::js
    var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
    $.ajax('api/search/tweets.json', {
      headers: xsrf,
      method: 'POST',
      data: {'q': 'gramener', 'count': '1'}
    })  // OUTPUT

The endpoint `/search/tweets.json` is the same as that in the Twitter API, which internally acts as an input to the `api` Gramex endpoint.

## Twitter followers

    :::js
    var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
    $.ajax('api/followers/list.json', {
      headers: xsrf,
      method: 'POST',
      data: {'screen_name': 'gramener'}
    })

## Parallel AJAX requests

The `TwitterRESTHandler` processes results asynchronously. So when one request
is being processed, it can process another as well.

Here, we send two requests. The time taken for both requests is almost the same
as the time taken for each individual request. They execute in parallel.

We use jQuery's [$.when](http://api.jquery.com/jQuery.when/) to wait for all
requests.

    :::js
    var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
    var q1 = $.ajax('api/search/tweets.json', {
      headers: xsrf,
      method: 'POST',
      data: {'q': 'gramener', 'count': '1'} // Latest tweet for Gramener
    })

    var q2 = $.ajax('api/search/tweets.json', {
      headers: xsrf,
      method: 'POST',
      data: {'q': 'RichardDawkins', 'count': '1'} // Latest tweet for Richard Dawkins
    })

    $.when(q1, q2) // OUTPUT


<script>
var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
var pre = [].slice.call(document.querySelectorAll('pre'))

function condense(result) {
  var field = [].concat(result)[0].statuses[0]
  return {
    'id_str'      : field.id_str,
    'created_at'  : field.created_at,
    'text'        : field.text,
    'user'        : {
        'name'      : field.user.name,
        'time_zone' : field.user.time_zone,
        '...'       : '...'
    },
    '...'         : '...'
  }
}


function replace(e, regex, text) {
    e.innerHTML = e.innerHTML.replace(regex, 
      '<p style="color: #ccc">// OUTPUT</p><p>' + text + '</p>')
}

function next() {
  var regex = /\/\/ OUTPUT/
  var element = pre.shift()
  // Behind the scenes, use GET instead of POST because we want to cache the requests
  var text = element.textContent.replace(/method: 'POST'/ig, "method: 'GET'")
  if (text.match(regex))
    if (text.match(/\$.when/)) {
      // Use GET to evaluate, since it can be cached
      eval(text).then(function(res1, res2) {
        var result = []
        for (var r of [res1, res2])
          result.push(condense(r))
        replace(element, regex, JSON.stringify(result, null, 2))
      })
    }
    else if (text.match(/\$.ajax/)) {
      eval(text).always(function(result) { replace(element, regex, JSON.stringify(condense(result), null, 2)) })
    }
  if (pre.length > 0) { next() }
}
next()
</script>
