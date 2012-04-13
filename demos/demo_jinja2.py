#!/usr/bin/env python

import sys
from brubeck.request_handling import Brubeck
from brubeck.templating import Jinja2Rendering, load_jinja2_env

class DemoHandler(Jinja2Rendering):
    def get(self):
        name = self.get_argument('name', 'dude')
        context = {
            'name': name,
        }
        return self.render_template('success.html', **context)

app = Brubeck(#mongrel2_pair=('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
              handler_tuples=[(r'^/brubeck', DemoHandler)],
              template_loader=load_jinja2_env('./templates/jinja2'))
#app.run()

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
    print "Serving on port 8001..."
    httpd.serve_forever()
