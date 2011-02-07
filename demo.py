#!/usr/bin/env python
#
# Copyright 2011 J2 Labs LLC. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY J2 Labs LLC ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL J2 Labs LLC OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of J2 Labs LLC.


"""This is a rough prototype
"""

import sys
import uuid

from brubeck import (Brubeck,
                     WebRequestHandler)
from mongrel2 import (Mongrel2Connection,
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
        self.set_status(200)
        return response
    
        
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
