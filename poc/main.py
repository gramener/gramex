import tornado.ioloop
import gramex

if __name__ == '__main__':
    # Configure application
    gramex.init()
    tornado.ioloop.IOLoop.current().start()
