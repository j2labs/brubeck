#!/usr/bin/env python


"""This is a rough prototype
"""

import sys

from brubeck.request_handling import Brubeck, WebMessageHandler

import logging
log_config = dict(#filename='brubeck.log',
                  level=logging.DEBUG)

logging.basicConfig(**log_config)

class DemoHandler(WebMessageHandler):
    def get(self):
        """Function called for HTTP GET"""
        logging.debug('DemoHandler.get() called')
        name = self.get_argument('name', 'whomever you are')
        self.set_body('Take five, %s!' % name)
        self.set_status(200)
        return self.render()

    def post(self):
        """Function called for HTTP POST. Requires username and password."""
        logging.debug('DemoHandler.post() calling .get()')
        return self.get()

        
if __name__ == '__main__':
    pull_addr = 'ipc://127.0.0.1:9999'
    pub_addr = 'ipc://127.0.0.1:9998'

    # Make sure mongrel2's config is in sync with this.
    handler_tuples = ((r'^/brubeck/', DemoHandler),)

    app = Brubeck((pull_addr, pub_addr), handler_tuples)
    app.run()
