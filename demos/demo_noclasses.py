#!/usr/bin/env python

import sys
from brubeck.request_handling import Brubeck, http_response

app = Brubeck(('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'))

@app.add_route('^/brubeck', method='GET')
def foo(application, message):
    name = message.get_argument('name', 'whomever you are')
    body = 'Take five, %s!' % name
    return http_response(body, 200, 'OK', {})
        
app.run()
