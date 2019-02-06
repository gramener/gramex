---
title: WebSocketHandler
prefix: WebSocketHandler
...

[TOC]

[WebSocketHandler][websockethandler] is used for persistent connections and
server-side push.

[See this chatbot demo](chat.html). The chatbot has a single connection to the
server that is kept open. This reduces latency. It also allows the server to send
a message back to the client when required.

Here is a sample configuration:

    :::yaml
    url:
        pingbot:
            pattern: /pingbot
            handler: WebSocketHandler
            kwargs:
                open:                               # When websocket is opened
                    function: pingbot.open          #   call open(handler) in pingbot.py
                on_message:                         # When client sends a message
                    function: pingbot.on_message    #   call on_message(handler, msg) in pingbot.py
                on_close:                           # When websocket is closed
                    function: pingbot.on_close      #   call on_close(handler) in pingbot.py
                origins:                            # Optional: Allow only from these domains.
                    - gramener.com                  # If unspecified, all domains are allowed.
                    - localhost
                    - 127.0.0.1
                # You can also add the auth: configuration like other handlers. For example:
                # auth: true

This passes on the `open`, `on_message` and `on_close` events to `pingbot.py`:

    :::python
    def open(handler):
        print('Chatbot opened for', handler.session['id'])

    def on_message(handler, message):
        print('Got message', message, 'for', handler.session['id'])
        handler.write_message('Got message: ' + message)

    def on_close(handler):
        print('Chatbot closed for', handler.session['id'])

Now we can use JavaScript to open and interact with the websocket.

    :::js
    // Open the websocket
    var url = location.href.replace(/^http/, 'ws') + 'pingbot'
    var ws = new WebSocket(url)

    // When we receive any message, log it to the console
    ws.onmessage = console.log

    // Send a message to the server a second later.
    setTimeout(function() {
      ws.send('Hello world')
    }, 1000)

    // You may use ws.close() to close the socket. Sockets automatically close
    // when the user closes the page, so this is not often used.
    // ws.close()

Now open this browser's JavaScript console. You should see the message returned by the server.

To learn more about websockets:

- Try this [Gramex chatbot](chat.html) and [view its source][chatbot-source]
- Learn how to write [WebSockets in JS][websocket-clients]

## Websockets via nginx

To serve WebSockets from behind an nginx reverse proxy, use the following config:

    http {
      # Add this configuration inside the http section
      # ----------------------------------------------
      map $http_upgrade $connection_upgrade {
          default upgrade;
          ''      close;
      }

      server {
        location / {
          proxy_pass ...;

          # Add this configuration inside the http > server > location section
          # ------------------------------------------------------------------
          proxy_http_version 1.1;
          proxy_set_header Upgrade    $http_upgrade;
          proxy_set_header Connection $connection_upgrade;
          proxy_set_header Host       $host;
          proxy_set_header X-Scheme   $scheme;
        }
      }
    }

[websockethandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.WebSocketHandler
[chatbot-source]: https://github.com/gramener/gramex/blob/dev/gramex/apps/guide/websockethandler/websocketchat.py
[websocket-clients]: https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_client_applications

<script>
var pre = [].slice.call(document.querySelectorAll('pre'))

function next() {
  var element = pre.shift(),
      text = element.textContent
  if (text.match(/new WebSocket/))
    eval(text)
  if (pre.length > 0) { next() }
}
next()
</script>
