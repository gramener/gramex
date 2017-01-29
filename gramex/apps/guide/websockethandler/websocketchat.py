import time
from random import choice
from tornado.ioloop import PeriodicCallback
from nltk.chat.util import Chat, reflections
from nltk.chat.eliza import pairs

chat_info = {}
idle_phrases = [
    "Are you still there?",
    "Would you like to say something?",
    "If you're busy, we can talk later.",
    "What are you thinking?",
    "Got distracted, did you?",
    "Let's change the topic. What makes you happy?",
    "Let's talk about something else. When did you last travel?",
    "Let's meditate for a few minutes.",
    "I'll take a short break. Ping me when you're back.",
]


def open(handler):
    # Send an introductory message
    handler.write_message('Hello. How are you feeling today?')
    # Set up chat configuration in the session
    chat = chat_info[handler.session['id']] = {
        # This is the Eliza bot that will converse with the user
        'bot': Chat(pairs, reflections),
        # The time at which the user last sent a message. Used for idle messages
        'time': time.time(),
        # Schedule a periodic check
        'callback': PeriodicCallback(idler(handler), callback_time=5000),
        # Send the next idle message after this many seconds.
        # This is doubled after every idle message, and reset when the user responds
        'delay': 10,
    }
    chat['callback'].start()


def on_message(handler, message):
    # When we receive a message, respond with the chatbot response
    chat = chat_info[handler.session['id']]
    handler.write_message(chat['bot'].respond(message))
    # Note the time of the last message. Reset the idle delay time
    chat.update(time=time.time(), delay=10)


def on_close(handler):
    # Stop periodic callback on
    session = handler.session['id']
    chat_info[session]['callback'].stop()
    chat_info.pop(session)


def idler(handler):
    # Return a method that can be called periodically to send idle messages.
    # The handler parameter we get here is stored to send future messages.
    def method():
        '''
        If delay seconds have elapsed since last message, send an idle message.
        Then double the delay so that we don't keep sending idle messages.
        '''
        now = time.time()
        chat = chat_info[handler.session['id']]
        if chat['time'] < now - chat['delay']:
            handler.write_message(choice(idle_phrases))
            chat['time'] = now
            chat['delay'] = chat['delay'] * 2
    return method
