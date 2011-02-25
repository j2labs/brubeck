#!/usr/bin/env python


"""This is a rough prototype
"""

import sys
import uuid

from brubeck.brubeck import (Brubeck,
                             WebRequestHandler)
from brubeck.mongrel2 import (Mongrel2Connection,
                              http_response)

import logging
log_config = dict(#filename='brubeck.log',
                  level=logging.DEBUG)

logging.basicConfig(**log_config)

class DemoHandler(WebRequestHandler):
    def get(self):
        logging.debug('DemoHandler.get called()')
        rev_msg = ''.join(reversed(self.request.path))
        logging.debug('  responding with: %s' % rev_msg)
        response = http_response(rev_msg, 200, rev_msg, {})        
        logging.debug('  HTTP msg ]--------------------\n%s' % response)
        self.set_status(200)
        return self.render()
    
        
if __name__ == '__main__':
    usage = 'usage: handling <pull address> <pub address>'
    if len (sys.argv) != 3:
        print usage
        sys.exit(1)

    #sender_id = '82209006-86FF-4982-B5EA-D1E29E55D481'
    sender_id = uuid.uuid4().hex
    pull_addr = sys.argv[1]
    pub_addr = sys.argv[2]

    m2conn = Mongrel2Connection(sender_id, pull_addr, pub_addr)

    # This part should match, at least, what mongrel2 is configured
    # to send
    request_handlers = ((r'^/brubeck/$', DemoHandler),)

    app = Brubeck(m2conn, request_handlers)
    app.run()
