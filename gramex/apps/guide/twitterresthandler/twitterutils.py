from textblob import TextBlob


def add_sentiment(result):
    for tweet in result['statuses']:
        blob = TextBlob(tweet['text'])
        tweet['sentiment'] = blob.sentiment.polarity
    return result
