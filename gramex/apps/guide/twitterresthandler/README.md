---
title: TwitterRESTHandler
prefix: TwitterRESTHandler
...

[TOC]

[TwitterRESTHandler][twitterresthandler] offers a proxy for the [Twitter 1.1 REST API](https://dev.twitter.com/rest/public). Here is an example:

    :::yaml
    url:
        twitter:
            pattern: /twitter/(.*)
            handler: TwitterRESTHandler
            kwargs:
                # Visit https://apps.twitter.com/ to get these keys
                key: '...'
                secret: '...'
            redirect:
                header: Referer
                url: /$YAMLURL/

Follow the steps for [Twitter auth](../auth/#twitter-auth) to get the keys above.

Now, follow these steps:

1. Click on [/twitter/search/tweets.json?q=beer](twitter/search/tweets.json?q=beer)
2. The first time you click on this, you get an "access token missing" error
3. So visit [/twitter/](twitter/) to log into Twitter
4. Now re-visit [/twitter/search/tweets.json?q=beer](twitter/search/tweets.json?q=beer)
5. This [searches for tweets][search-tweets] about beer

## Twitter Pre-auth

If you don't want the user to log in, and want to use a pre-authorised login, add
the following to the `kwargs:` section:

    :::yaml
    url:
        twitter-open:
            pattern: /twitter-open/(.*)
            handler: TwitterRESTHandler
            kwargs:
                # Visit https://apps.twitter.com/ to get these keys
                key: '...'
                secret: '...'
                access_key: '...'
                access_secret: '...'

Now
[/twitter-open/search/tweets.json?q=beer](twitter-open/search/tweets.json?q=beer)
even without you logging into Twitter. It runs on behalf of the developer with
their access token.

To use this via jQuery, use this snippet:

    :::js
    $.get('twitter-open/statuses/home_timeline.json?count=1')
    // OUTPUT

## Twitter Paths

To hard-code a specific REST API, use the `path:` parameter. For example:

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

[search-tweets]: https://dev.twitter.com/rest/reference/get/search/tweets

## Twitter OAuth

A typical Twitter app page will have the following flow:

1. Fetch the response via an AJAX query to the TwitterHandler
2. If there's no error, display the response
3. If there's an error,
    - if the access token is missing, ask the user to log in

For example:

    :::js
    $.get('twitter/statuses/home_timeline.json')
     .done(function(data) { display(data) })
     .fail(function(xhr, status, msg) {
        if (msg == 'access token missing')
          location.href = 'twitter/'          // Redirect the user to log in
        else
          alert(msg)                          // Alert if it's some other error
      })

After the login, users can be redirected via the `redirect:` config
documented the [redirection configuration](../config/#redirection).

## Twitter Persist

If your app needs to persist the user's access token, add `access_key: persist`
and `access_secret: persist` to the kwargs. The first time, the user is asked to
log in. Thereafter, the user's credentials are available for all future requests.

This is typically used to show authenticated information on behalf of a user to
the public. Typically, such requests are cached as well. Here is a sample
configuration:

    :::yaml
    url:
      twitter-persist:
        pattern: /persist/(.*)
        handler: TwitterRESTHandler
        kwargs:
            key: '...'
            secret: '...'
            access_key: persist       # Persist the access token after first login
            access_secret: persist    # Persist the access token after first login
        cache:
            duration: 300             # Cache requests for 5 seconds

Here is a sample response:

    :::js
    $.get('persist/statuses/home_timeline.json?count=1')  // OUTPUT

The first time, you get an access_key error. Visit [/persist/](persist/) to log
in. Thereafter, your access_key and access_secret will be stored and used for
future requests until it expires, or a user logs in again at
[/persist/](persist/).

## Twitter search

The following request [searches](https://dev.twitter.com/rest/reference/get/search/tweets) for mentions of Gramener and fetches the first response:

    :::js
    $.get('twitter-open/search/tweets.json?q=gramener&count=1')  // OUTPUT

The endpoint `/search/tweets.json` is the same as that in the Twitter API, which internally acts as an input to the `api` Gramex endpoint.

## Twitter followers

This script fetches the [list of followers](https://dev.twitter.com/rest/reference/get/followers/list) for Gramener:

    :::js
    $.get('twitter-open/followers/list.json?screen_name=gramener&count=1')  // OUTPUT

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
              sentiment:
                  function: twitterutils.add_sentiment

Here's what `twitterutils.add_sentiment` looks for the last about Gramener:

    :::python
    from textblob import TextBlob
    def add_sentiment(result, handler):
        for tweet in result['statuses']:
            blob = TextBlob(tweet['text'])
            tweet['sentiment'] = blob.sentiment.polarity
        return result

This transforms the tweets to add a `sentiment:` key measuring its sentiment.

    :::js
    $.get('sentiment?q=gramener&count=1')  // OUTPUT

The transform should either return a JSON-encodable object, or a string.

Transforms are executed in a separate thread. This makes the application more responsive. But you need to ensure that your code is thread-safe.

To append all tweets into a JSON-Line file, use a function like this:

    :::python
    def save_tweet_transform(result, handler):
        with open('tweets.jsonl', 'a') as out:
            for status in result['statuses']:
              json.dump(status, out + '\n')
        return result

You can then include this in the TwitterHandler transform section as follows:

    :::yaml
        ...
        kwargs:
          transform:
              sentiment:
                  function: module.save_tweet_transform


## Parallel AJAX requests

The `TwitterRESTHandler` processes results asynchronously. So when one request
is being processed, it can process another as well.

Here, we send two requests. The time taken for both requests is almost the same
as the time taken for each individual request. They execute in parallel.

We use jQuery's [$.when](http://api.jquery.com/jQuery.when/) to wait for all
requests.

    :::js
    // Latest tweet for Gramener
    var q1 = $.get('twitter-open/search/tweets.json?q=gramener&count=1')
    // Latest tweet for Richard Dawkins
    var q2 = $.get('twitter-open/search/tweets.json?q=RichardDawkins&count=1')
    $.when(q1, q2) // OUTPUT

## Twitter GET requests

The `methods:` parameter specifies which methods to use to access the API. The
default is `[GET, POST]`. You can replace it with `[POST]` to just use POST. This
prevents external sites from requesting the page. Note that you need to handle
[XSRF](../filehandler/#xsrf) for POST requests.

    :::yaml
    url:
        twitter:
            pattern: /twitter/search          # Maps this URL
            handler: TwitterRESTHandler
            kwargs:
                ...
                methods: [POST]               # Allow only POST requests

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
                flush: 60                       # Flush data every 60 seconds
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

var pre = [].slice.call(document.querySelectorAll('pre'))

function next() {
  var output_regex = /\/\/ OUTPUT/,
      element = pre.shift(),
      text = element.textContent

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
    else if (text.match(/\$.(ajax|get)/)) {
      eval(text).always(function(result) {
        replace(element, output_regex, JSON.stringify(condense(result), null, 2))
      })
    }
  if (pre.length > 0) { next() }
}
next()
</script>

[twitterresthandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.TwitterRESTHandler
