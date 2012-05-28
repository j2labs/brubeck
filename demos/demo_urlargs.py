#!/usr/bin/env python


from brubeck.request_handling import Brubeck, WebMessageHandler, render
from brubeck.connections import Mongrel2Connection
import sys


class IndexHandler(WebMessageHandler):
    def get(self):
        self.set_body('Take five!')
        return self.render()

class NameHandler(WebMessageHandler):
    def get(self, name):
        self.set_body('Take five, %s!' % (name))
        return self.render()

def name_handler(application, message, name):
    return render('Take five, %s!' % (name), 200, 'OK', {})


urls = [(r'^/class/(\w+)$', NameHandler),
        (r'^/fun/(?P<name>\w+)$', name_handler),
        (r'^/$', IndexHandler)]

config = {
    'msg_conn': Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
    'handler_tuples': urls,
}

app = Brubeck(**config)


@app.add_route('^/deco/(?P<name>\w+)$', method='GET')
def new_name_handler(application, message, name):
    return render('Take five, %s!' % (name), 200, 'OK', {})


app.run()
