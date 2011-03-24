#!/usr/bin/env python

import sys
from brubeck.request_handling import Brubeck, WebMessageHandler

class DemoHandler(WebMessageHandler):
    def get(self):
        name = self.get_argument('name', 'whomever you are')
        self.set_body('Take five, %s!' % name)
        self.set_status(200)
        return self.render()

app = Brubeck(('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
              handler_tuples=[(r'^/brubeck', DemoHandler)])
app.run()
