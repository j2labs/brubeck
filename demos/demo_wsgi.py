#!/usr/bin/env python

import sys
import os
from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.connections import WSGIConnection

class DemoHandler(WebMessageHandler):
    def get(self):
        name = self.get_argument('name', 'dude')
        self.set_body('Take five, %s!' % name)
        return self.render()

config = {
    'msg_conn': WSGIConnection(),
    'handler_tuples': [(r'^/brubeck', DemoHandler)],
}

app = Brubeck(**config)
app.run()
