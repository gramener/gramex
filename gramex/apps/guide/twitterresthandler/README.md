title: Gramex accesses Twitter data

`TwitterRESTHandler` offers a proxy for the [Twitter 1.1 REST API](https://dev.twitter.com/rest/public), with the added advantage of being asynchronous. Here is an example:

    :::yaml
    url:
        twitter:
            pattern: /twitter/(.*)
            handler: TwitterRESTHandler
            kwargs:
                # Visit https://apps.twitter.com/ to get these keys
                key: '...'
                secret: '...'
                access_key: '...'
                access_secret: '...'

Follow the steps for [Twitter auth](../auth/#twitter-auth) to get the keys above.

Now, `POST /twitter/search/tweets.json?q=beer` will 
[search for tweets][search-tweets] about beer.
It's the same as `GET https://api.twitter.com/1.1/search/tweets.json?q=beer`,
but pre-authenticated with the keys provided in `kwargs`.

To use just a specific REST API, use the `path:` parameter. For example:

    :::yaml
    url:
        twitter:
            pattern: /twitter/search          # Maps this URL
            handler: TwitterRESTHandler
            kwargs:
                path: search/tweets.json      # specifically to the API 
                ...

... maps `/twitter/search` to `https://api.twitter.com/1.1/search/tweets.json`
with the relevant authentication.

The examples below use [jQuery.ajax][jquery-ajax] and the [cookie.js][cookie.js] libraries.

[jquery-ajax]: http://api.jquery.com/jquery.ajax/
[cookie.js]: https://github.com/florian/cookie.js
[search-tweets]: https://dev.twitter.com/rest/reference/get/search/tweets

<script src="https://cdnjs.cloudflare.com/ajax/libs/cookie.js/1.2.0/cookie.min.js"></script>

## Twitter search

The following request [searches](https://dev.twitter.com/rest/reference/get/search/tweets) for metnions of Gramener and fetches the first response:

    :::js
    var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
    $.ajax('api/search/tweets.json', {
      headers: xsrf,
      method: 'POST',
      data: {'q': 'gramener', 'count': '1'}
    })  // OUTPUT

The endpoint `/search/tweets.json` is the same as that in the Twitter API, which internally acts as an input to the `api` Gramex endpoint.

## Twitter followers

This script fetches the [list of followers](https://dev.twitter.com/rest/reference/get/followers/list) for Gramener:

    :::js
    var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
    $.ajax('api/followers/list.json', {
      headers: xsrf,
      method: 'POST',
      data: {'screen_name': 'gramener'}
    })

## Twitter transforms

You can use the `transform:` configuration to modify the response in any way. Here is a simple transform that adds the sentiment to each tweet:

    :::yaml
    twittersentiment:
        pattern: /$YAMLURL/sentiment
        handler: TwitterRESTHandler
        kwargs:
          ...
          path: search/tweets.json
          transform:
            function: twitterutils.add_sentiment

Here's what `twitterutils.add_sentiment` looks for the last about Gramener:

    :::python
    from textblob import TextBlob
    def add_sentiment(result):
        for tweet in result['statuses']:
            blob = TextBlob(tweet['text'])
            tweet['sentiment'] = blob.sentiment.polarity
        return result

This transforms the tweets to add a `sentiment:` key measuring its sentiment.

    :::js
    var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
    $.ajax('sentiment', {
      headers: xsrf,
      method: 'POST',
      data: {'q': 'gramener', 'count': '1'}
    })  // OUTPUT

The transform should either return a JSON-encodable object, or a string.

Transforms are executed in a separate thread. This makes the application more responsive. But you need to ensure that your code is thread-safe.


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

## Twitter GET requests

The `methods:` parameter specifies which methods to use to access the API. The
default is just `POST`. You can replace it with `[GET, POST]` to use either
GET or POST, or `GET` to use only the `GET` HTTP method.

This example lets you use either GET or POST requests.

    :::yaml
    url:
        twitter:
            pattern: /twitter/search          # Maps this URL
            handler: TwitterRESTHandler
            kwargs:
                ...
                methods: [GET, POST]          # Allows using GET and POST requests

## Twitter OAuth

The above examples allowed you to query Twitter with a pre-defined access token.
But for users to use their own account to access the API, do the following:

1. Create a `TwitterRESTHandler` at a URL (e.g.
   [oauth-api/](oauth-api/?next=../)). Do not specify an `access_key` or
   `access_secret`. It will redirect the user to Twitter and log them in.
2. Any request now made to `oauth-api/...` will use the user's access token.

The first time you make a request to `/oauth-api/` (see below), you will see an
error message saying `access token missing`. But visit
[oauth-api/?next=../](oauth-api/) and log into Twitter. Then the request below
will return the first tweet on your timeline.

    :::js
    var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
    $.ajax('oauth-api/statuses/home_timeline.json', {
      headers: xsrf,
      method: 'POST',
      data: {'count': '1'}
    })  // OUTPUT


## Twitter streaming

The [Twitter streaming API](https://dev.twitter.com/streaming/overview) provides
a live source of tweets. This can be set up as a schedule:

    :::yaml
    schedule:
        twitter-stream:
            function: TwitterStream
            kwargs:
                track: beer,wine                # Track these keywords
                follow: Starbucks,Microsoft     # OR follow these users' tweets
                path: tweets.{:%Y-%m-%d}.jsonl  # Save the results in this file
                # Visit https://apps.twitter.com/ to get these keys
                key: ...
                secret: ...
                access_key: ...
                access_secret: ...
            startup: true                       # Run on startup
            thread: true                        # in a separate thread (REQUIRED)

This runs the `TwitterStream` class on startup in a separate thread.
`TwitterStream` opens a permanent connection to Twitter and receives all tweets
matching either `beer` or `wine`. It also receives any tweets from `@Starbucks`
and `@Microsoft`.

The results are saved in `tweets.xxx.jsonl`. (The extension `.jsonl` indicates
the [JSON Lines](http://jsonlines.org/) format.) You can use standard Python
[date formatting](http://strftime.org/). For example, `{:%b-%Y}.jsonl` will
create files like `Jan-2016.jsonl`, `Feb-2016.jsonl`, etc. while `{:%H-%M}.jsonl`
will save the tweets into an hour-minute files. (It will append to the file, so
you won't lose data.)

Note: You can run multiple Twitter streams, but you need different access keys
for each.


<script>
var xsrf = {'X-Xsrftoken': cookie.get('_xsrf')}
var pre = [].slice.call(document.querySelectorAll('pre'))

function condense(result) {
  var field = [].concat(result)[0]
  field = field.statuses ? field.statuses[0] : field
  if (!field || !field.user)
    return result
  result = {
    'id_str'      : field.id_str,
    'created_at'  : field.created_at,
    'text'        : field.text,
    'user'        : {
        'name'      : field.user ? field.user.name : '',
        'time_zone' : field.user ? field.user.time_zone : '',
        '...'       : '...'
    },
    '...'         : '...'
  }
  if ('sentiment' in field)
    result.sentiment = field.sentiment
  return result
}


function replace(e, regex, text) {
    e.innerHTML = e.innerHTML.replace(regex, 
      '<p style="color: #ccc">// OUTPUT</p><p>' + text + '</p>')
}

function next() {
  var output_regex = /\/\/ OUTPUT/,
      element = pre.shift(),
      text = element.textContent

  // Behind the scenes, use GET instead of POST because we want to cache the requests.
  // But only for /api/, not for /oauth-api/
  if (!text.match(/oauth-api/))
    text = text.replace(/method: 'POST'/ig, "method: 'GET'")

  if (text.match(output_regex))
    if (text.match(/\$.when/)) {
      // Use GET to evaluate, since it can be cached
      eval(text).then(function(res1, res2) {
        var result = []
        for (var r of [res1, res2])
          result.push(condense(r))
        replace(element, output_regex, JSON.stringify(result, null, 2))
      })
    }
    else if (text.match(/\$.ajax/)) {
      eval(text).always(function(result) {
        replace(element, output_regex, JSON.stringify(condense(result), null, 2))
      })
    }
  if (pre.length > 0) { next() }
}
next()
</script>
