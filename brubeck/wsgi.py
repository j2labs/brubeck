from request import Request
from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server


def receive_wsgi_req(environ, start_response):
    request = Request.parse_wsgi_request(environ)
    return [request]


class WSGIConnection(object):
    """This class defines request handling methods for wsgi implimentations."""

    def __init__(self, port=8000):
        self.port = port

    def recv(self, environ, start_response):
        """Receives the request from the wsgi server."""
        setup_testing_defaults(environ)

        status = '200 OK'
        headers = [('Content-type', 'text/plain')]

        start_response(status, headers)

        ret = ["%s: %s\n" % (key, value)
               for key, value in environ.iteritems()]
        return ret

if __name__ == "__main__":
    wsgi_conn = WSGIConnection()
    httpd = make_server('', 8000, wsgi_conn.recv)
    print "Serving on port 8000..."
    httpd.serve_forever()
