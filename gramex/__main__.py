'Run Gramex from current path'
import tornado.ioloop
from gramex import init

init(path='gramex.yaml')
tornado.ioloop.IOLoop.current().start()
