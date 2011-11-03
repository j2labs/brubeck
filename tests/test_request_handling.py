#!/usr/bin/env python

import unittest
import sys
import brubeck
from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.mongrel2 import to_bytes, Request
from brubeck.request_handling import cookie_encode, cookie_decode, cookie_is_encoded, http_response

""" our simple messages for testing """
HTTP_REQUEST_BRUBECK_MESSAGE = '34f9ceee-cd52-4b7f-b197-88bf2f0ec378 3 /brubeck 508:{"PATH":"/brubeck","x-forwarded-for":"127.0.0.1","cache-control":"max-age=0","accept-language":"en-US,en;q=0.8","accept-encoding":"gzip,deflate,sdch","connection":"keep-alive","accept-charset":"ISO-8859-1,utf-8;q=0.7,*;q=0.3","accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","user-agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.106 Safari/535.2","host":"127.0.0.1:6767","METHOD":"GET","VERSION":"HTTP/1.1","URI":"/brubeck","PATTERN":"/"},0:,\n'

HTTP_REQUEST_ROOT_MESSAGE = '34f9ceee-cd52-4b7f-b197-88bf2f0ec378 5 / 466:{"PATH":"/","x-forwarded-for":"127.0.0.1","accept-language":"en-US,en;q=0.8","accept-encoding":"gzip,deflate,sdch","connection":"keep-alive","accept-charset":"ISO-8859-1,utf-8;q=0.7,*;q=0.3","accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","user-agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.106 Safari/535.2","host":"127.0.0.1:6767","METHOD":"GET","VERSION":"HTTP/1.1","URI":"/","PATTERN":"/"},0:,\n'

HTTP_REQUEST_ROOT_MESSAGE_WITH_COOKIE = '34f9ceee-cd52-4b7f-b197-88bf2f0ec378 5 / 487:{"PATH":"/","x-forwarded-for":"127.0.0.1","accept-language":"en-US,en;q=0.8","accept-encoding":"gzip,deflate,sdch","connection":"keep-alive","accept-charset":"ISO-8859-1,utf-8;q=0.7,*;q=0.3","accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","user-agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.106 Safari/535.2","host":"127.0.0.1:6767","cookie":"key=value","METHOD":"GET","VERSION":"HTTP/1.1","URI":"/","PATTERN":"/"},0:,\n'

HTTP_RESPONSE_OBJECT_ROOT_MESSAGE = 'HTTP/1.1 200 OK\r\nContent-Length: 29\r\n\r\nTake five dude object handler'
HTTP_RESPONSE_METHOD_ROOT_MESSAGE = 'HTTP/1.1 200 OK\r\nContent-Length: 29\r\n\r\nTake five dude method handler'

HTTP_RESPONSE_OBJECT_ROOT_MESSAGE_WITH_COOKIE = 'HTTP/1.1 200 OK\r\nSet-Cookie: key=value\r\nContent-Length: 29\r\n\r\nTake five dude object handler'

""" our test body text """
TEST_BODY_METHOD_HANDLER="Take five dude method handler"
TEST_BODY_OBJECT_HANDLER="Take five dude object handler"

###
### Message handling (non)coroutines for testing
###

def route_message(application, message):
    handler = application.route_message(message)
    return request_handler(application, message, handler)

def request_handler(application, message, handler):
    if callable(handler):
        return handler()

class MockPool(object):
    """" create a mock pool to allow a brubeck object to be instanciated  """
    """ we won't really use it in practice """
    def __init__(self):
        pass
    def __call__(self, msg, route):
        pass
    def spawn_n(function, app, message, *a, **kw):
        pass
    def spawn(function, app, message, *a, **kw):
        pass

class SimpleHandlerObject(WebMessageHandler):
    def get(self):
        self.set_body(TEST_BODY_OBJECT_HANDLER)
        return self.render()

class CookieHandlerObject(WebMessageHandler):
    def get(self):
        self.set_cookie("key", self.get_cookie("key"));
        self.set_body(TEST_BODY_OBJECT_HANDLER)
        return self.render()

class CookieAddHandlerObject(WebMessageHandler):
    def get(self):
        self.set_cookie("key", "value");
        self.set_body(TEST_BODY_OBJECT_HANDLER)
        return self.render()


class MockMessage(object):
    """ we are a static zmq message """
    def __init__(self, path = '/', msg = HTTP_REQUEST_ROOT_MESSAGE):
        self.path = path
        self.msg = msg

    def get(self):
       return self.msg
        
class TestRequestHandling(unittest.TestCase):
    """
    a test class for brubeck's request_handler
    """

    def setUp(self):
        """
        will get run for each test
        """
        mock_pool = MockPool()
        config = {
            'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
            ## 'pool': mock_pool,
        }
        self.app = Brubeck(**config)

    """ our actual tests( test _xxxx_xxxx(self) ) """
    def test_add_route_rule_method(self):
	""" Make sure we have no routes """
        self.assertEqual(hasattr(self.app,'_routes'),False)

        self.setup_route_with_method()

        """ Make sure we have some routes """
        self.assertEqual(hasattr(self.app,'_routes'),True)

        """ Make sure we have exactly one route """
        self.assertEqual(len(self.app._routes),1)

    def test_init_routes_with_methods(self):
        """ Make sure we have no routes """
        self.assertEqual(hasattr(self.app, '_routes'), False)

        """ Create a tuple """
        routes = [ (r'^/', self.route_handler_method), (r'^/brubeck', self.route_handler_method) ]
        self.app.init_routes( routes )

        """ Make sure we have two routes """
        self.assertEqual(len(self.app._routes), 2)

    def test_init_routes_with_objects(self):
        """ Make sure we have no routes """
        self.assertEqual(hasattr(self.app, '_routes'), False)

        """ Create a tuple of routes with object handlers """
        routes = [(r'^/', SimpleHandlerObject), (r'^/brubeck', SimpleHandlerObject)]
        self.app.init_routes( routes )

        """ Make sure we have two routes """
        self.assertEqual(len(self.app._routes), 2)

    def test_init_routes_with_objects_and_methods(self):
        """ Make sure we have no routes """
        self.assertEqual(hasattr(self.app, '_routes'), False)

        """ Create a tuple of routes with method handlers """
        routes = [(r'^/', SimpleHandlerObject), (r'^/brubeck', self.route_handler_method)]
        self.app.init_routes( routes )

        """ Make sure we have two routes """
        self.assertEqual(len(self.app._routes), 2)


    def test_add_route_rule_object(self):
        """ Make sure we have no routes """
        self.assertEqual(hasattr(self.app,'_routes'),False)
        self.setup_route_with_object()

        """ Make sure we have some routes """
        self.assertEqual(hasattr(self.app,'_routes'),True)

        """ Make sure we have exactly one route """
        self.assertEqual(len(self.app._routes),1)

    def test_brubeck_handle_request_with_object(self):
        """ We ran tests on this already, so assume it works """
        self.setup_route_with_object()

        """ Make sure we get a handler back when we request one """
        message = MockMessage(path='/')
        handler = self.app.route_message(message)
        self.assertNotEqual(handler,None)

    def test_brubeck_handle_request_with_method(self):
        """ We ran tests on this already, so assume it works """
        self.setup_route_with_method()

        """ Make sure we get a handler back when we request one """
        message = MockMessage(path='/')
        handler = self.app.route_message(message)
        self.assertNotEqual(handler,None)

    def test_cookie_handling(self):
        cookie_key = 'my_key'
        cookie_value = 'my_secret'

        unencoded_cookie = to_bytes('!') + to_bytes(cookie_key) + to_bytes('?') + to_bytes(cookie_value)
        encoded_cookie = cookie_encode(cookie_value, cookie_key)

        """ Make sure we do not contain our value (i.e. we are really encrypting) """
        self.assertEqual(encoded_cookie.find(cookie_value) == -1, True)

        """ Make sure we are an encoded cookie using the function """
        self.assertEqual(cookie_is_encoded(encoded_cookie), True)

        """ Make sure after decoding our cookie we are the same as the unencoded cookie """
        decoded_cookie = cookie_decode(encoded_cookie, cookie_key)
        self.assertEqual(decoded_cookie, cookie_value)

    def test_request_handling_with_object(self):
        self.setup_route_with_object()
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT_MESSAGE))
        self.assertEqual(HTTP_RESPONSE_OBJECT_ROOT_MESSAGE, response)

    def test_request_handling_with_method(self):
        self.setup_route_with_method()
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT_MESSAGE))
        self.assertEqual(HTTP_RESPONSE_METHOD_ROOT_MESSAGE, response)

    def test_request_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/',CookieHandlerObject)
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT_MESSAGE_WITH_COOKIE))
        self.assertEqual(HTTP_RESPONSE_OBJECT_ROOT_MESSAGE_WITH_COOKIE, response)

    def test_request_with_cookie_response_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/',CookieHandlerObject)
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT_MESSAGE_WITH_COOKIE))
        self.assertEqual(HTTP_RESPONSE_OBJECT_ROOT_MESSAGE_WITH_COOKIE, response)

    def test_request_without_cookie_response_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/',CookieAddHandlerObject)
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT_MESSAGE))
        self.assertEqual(HTTP_RESPONSE_OBJECT_ROOT_MESSAGE_WITH_COOKIE, response)

    def test_build_http_response(self):
        response = http_response(TEST_BODY_OBJECT_HANDLER, 200, 'OK', dict())
        self.assertEqual(HTTP_RESPONSE_OBJECT_ROOT_MESSAGE, response)

    """ some helper functions """
    def route_handler_method(self, application, *args):
        """" dummy request action """
        return http_response(TEST_BODY_METHOD_HANDLER, 200, 'OK', dict())

    def setup_route_with_object(self, url_pattern='^/'):
        self.app.add_route_rule(url_pattern,SimpleHandlerObject)

    def setup_route_with_method(self, url_pattern='^/'):
        method = self.route_handler_method
        self.app.add_route_rule(url_pattern, method)

""" This will run our tests """
if __name__ == '__main__':
    unittest.main()
