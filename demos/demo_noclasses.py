#!/usr/bin/env python

from brubeck.request_handling import Brubeck, render
from brubeck.connections import Mongrel2Connection

app = Brubeck(msg_conn=Mongrel2Connection('tcp://127.0.0.1:9999',
                                          'tcp://127.0.0.1:9998'))

@app.add_route('^/brubeck', method='GET')
def foo(application, message):
    name = message.get_argument('name', 'dude')
    body = 'Take five, %s!' % name
    return render(body, 200, 'OK', {})
        
app.run()
