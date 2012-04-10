from brubeck.request import Request
from brubeck.request_handling import coro_spawn, route_message


def receive_wsgi_req(environ, start_response):
    request = Request.parse_wsgi_request(environ)
    coro_spawn(route_message, self, request)

class WSGIConnection(object):
    """This class defines request handling methods for wsgi implimentations."""

    def __init__(self):
        pass

    def recv(self):
        """Receives the request from the wsgi server."""
        pass

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

    httpd = make_server('', 8000, receive_wsgi_req)
    print "Serving on port 8000..."
    httpd.serve_forever()
