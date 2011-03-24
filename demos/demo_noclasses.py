#!/usr/bin/env python

import sys
from brubeck.request_handling import Brubeck, http_response

app = Brubeck(mongrel2_pair=('ipc://127.0.0.1:9999',  # PULL requests <- M2
                             'ipc://127.0.0.1:9998')) # PUB responses -> M2

@app.add_route('^/brubeck', method='GET')
def foo(application, message):
    name = message.get_argument('name', 'dude')
    body = 'Take five, %s!' % name
    return http_response(body, 200, 'OK', {})
        
app.run()
