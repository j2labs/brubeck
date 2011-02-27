#!/usr/bin/env python


"""This is a rough prototype
"""

import sys

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.mongrel2 import Mongrel2Connection, http_response

import logging
log_config = dict(#filename='brubeck.log',
                  level=logging.DEBUG)

logging.basicConfig(**log_config)

class DemoHandler(WebMessageHandler):
    def get(self):
        logging.debug('DemoHandler.get() called')
        name = self.get_argument('name', 'whomever you are')
        self.set_body('Take five, %s!' % name)
        self.set_status(200)
        return self.render()

    def post(self):
        logging.debug('DemoHandler.post() called')
        return self.get()

        
if __name__ == '__main__':
    usage = 'usage: handling <pull address> <pub address>'
    if len (sys.argv) != 3:
        print usage
        sys.exit(1)

    pull_addr = sys.argv[1]
    pub_addr = sys.argv[2]

    # Make sure mongrel2's config is in sync with this.
    handler_tuples = ((r'^/brubeck/$', DemoHandler),)

    app = Brubeck((pull_addr, pub_addr), handler_tuples)
    app.run()
