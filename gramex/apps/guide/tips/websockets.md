---
title: Websockets in Gramex
prefix: Tip
...

We can use websockets to persist bidirectional connections with server. [WebSocketHandler docs](https://learn.gramener.com/guide/websockethandler/).

**How can this be useful?**

Useful for real-time applications: insights or feed or data extraction, chat bots.

Gramex supports Websockets - YAML

    :::yaml
    url:
      ws/load:
        pattern: /$YAMLURL/ws
        handler: WebSocketHandler
        kwargs:
            open:
                function: app.ws_open
            on_message:
                function: app.ws_on_message
            on_close:
                function: app.close
            auth: true

**Send a request - Javascript**

    :::js
    protocols = {http: 'ws://', https: 'wss://'}
    ws = new WebSocket(protocols[window.location.protocol] + window.location.hostname + ":" + window.location.port + "/ws")

    :::js
    // this maps to yaml definition of kwargs.open which maps to app.open()
    ws.onopen = function() {
      // your code
    }

    :::js
    ws.onmessage = function() {
      // your functionality
    }

    :::js
    ws.onerror = function() {
      // error handling
    }

Requests are served as they are complete. Examples of backend can be found for Autolysis below.

**Do we already use it?**

[Google search](https://uat.gramener.com/google-search/) [[code](https://code.gramener.com/sanjay.yadav/google-search/blob/dev/js/script.js#L7) - client]. Each search result for a keyword/domain combination is fetched over a websocket connection.

[Autolysis](https://uat.gramener.com/autolysis/) [[code](https://code.gramener.com/autolysis/autowrapper/blob/master/autolysis_server.py) - server]. Each [groupmeans cell here](https://uat.gramener.com/autolysis/insights/?analysis=groupmeans&key=BNEXRSDUPYNA) is yielded over a websocket connection.
