---
title: Schedule tasks at periodic intervals
prefix: Tip
...

As a service, Gramex can schedule tasks at regular intervals (lowest granularity at minute level) that can be configured as:

    :::yaml
    # your friendly configuration to post a Tweet every day at 7:15 am
    run-at-your-interval:
        function: scraper.post_tweet
        startup: true    # also runs this section when Gramex is instantiated, use if required
        hours: '7'       # 7th hour of every day
        minutes: '15'    # 15th minute of that hour
        thread: true

## Use-cases

- email insights every Wednesday
- data refresh at regular intervals
- post a tweet at 7:15 am every day

## Current uses

Data refresh [scheduled](https://code.gramener.com/vijay.yellepeddi/network18-elections/blob/master/refresh_data.py#L173)
for [every minute](https://code.gramener.com/vijay.yellepeddi/network18-elections/blob/master/gramex.yaml#L10) in Network-18.
