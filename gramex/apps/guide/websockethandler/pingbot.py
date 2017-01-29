def open(handler):
    print('Chatbot opened for', handler.session['id'])              # noqa


def on_message(handler, message):
    print('Got message', message, 'for', handler.session['id'])     # noqa
    handler.write_message('Got message: ' + message)


def on_close(handler):
    print('Chatbot closed for', handler.session['id'])              # noqa
