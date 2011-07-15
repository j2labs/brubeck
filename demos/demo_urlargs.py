#!/usr/bin/env python


import sys

from brubeck.request_handling import Brubeck, WebMessageHandler, http_response


class IndexHandler(WebMessageHandler):
    def get(self):
        self.set_body('Take five!')
        return self.render()

class NameHandler(WebMessageHandler):
    def get(self, name):
        self.set_body('Take five, %s!' % (name))
        return self.render()

def name_handler(application, message, name):
    return http_response('Take five, %s!' % (name), 200, 'OK', {})


urls = [(r'^/class/(\w+)$', NameHandler),
        (r'^/fun/(?P<name>\w+)$', name_handler),
        (r'^/', IndexHandler)]

config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': urls,
}

app = Brubeck(**config)


@app.add_route('^/deco/(?P<name>\w+)$', method='GET')
def new_name_handler(application, message, name):
    return http_response('Take five, %s!' % (name), 200, 'OK', {})


app.run()
