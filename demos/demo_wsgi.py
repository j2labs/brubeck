#!/usr/bin/env python

import sys
sys.path = ["/home/steve/brub/brubeck/"] + sys.path
from brubeck.request_handling import Brubeck, WebMessageHandler

class DemoHandler(WebMessageHandler):
    def get(self):
        name = self.get_argument('name', 'dude')
        self.set_body('Take five, %s!' % name)
        return self.render()

config = {
#    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^/brubeck', DemoHandler)],
}
app = Brubeck(**config)

if __name__ == "__main__":
    from wsgiref.util import setup_testing_defaults
    from wsgiref.simple_server import make_server
    def simple_app(environ, start_response):
        setup_testing_defaults(environ)

        status = '200 OK'
        headers = [('Content-type', 'text/plain')]

        start_response(status, headers)

        ret = ["%s: %s\n" % (key, value)
               for key, value in environ.iteritems()]
        return ret

    httpd = make_server('', 8001, app.receive_wsgi_req)
    print "Serving on port 8000..."
    httpd.serve_forever()
