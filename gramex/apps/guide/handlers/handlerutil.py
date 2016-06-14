from collections import Counter
from gramex.handlers import BaseHandler


class CustomHandler(BaseHandler):
    def get(self):
        self.write('This is a custom handler')


class SetupHandler(BaseHandler):
    @classmethod
    def setup(cls, **kwargs):
        super(SetupHandler, cls).setup(**kwargs)        # You MUST call the BaseHandler setup
        cls.name = kwargs.get('name', 'NA')             # Perform any one-time setup here
        cls.count = Counter()

    def initialize(self, **kwargs):                     # initialize() is called with same kwargs
        super(SetupHandler, self).initialize(**kwargs)  # You MUST call the BaseHandler initialize
        self.count[self.name] += 1                      # Perform any recurring operations here

    def get(self):
        self.write('Name %s was called %d times' % (self.name, self.count[self.name]))
