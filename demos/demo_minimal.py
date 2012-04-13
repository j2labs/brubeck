#!/usr/bin/env python

import sys
from brubeck.request_handling import Brubeck, WebMessageHandler

class DemoHandler(WebMessageHandler):
    def get(self):
        name = self.get_argument('name', 'dude')
        self.set_body('Take five, %s!' % name)
        return self.render()

config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^/brubeck', DemoHandler)],
}
app = Brubeck(**config)
app.run()
