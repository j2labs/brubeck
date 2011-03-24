#!/usr/bin/env python


"""This is a rough prototype
"""

import sys

from brubeck.request_handling import Brubeck, http_response

import logging
logging.basicConfig(**{'level': logging.DEBUG})

pull_addr = 'ipc://127.0.0.1:9999'
pub_addr = 'ipc://127.0.0.1:9998'

app = Brubeck((pull_addr, pub_addr))

@app.add_route('^/brubeck', method='GET')
def foo(application, message):
    logging.debug('foo() called')
    name = message.get_argument('name', 'whomever you are')
    body = 'Take five, %s!' % name
    return http_response(body, 200, 'OK', {})
        
app.run()
