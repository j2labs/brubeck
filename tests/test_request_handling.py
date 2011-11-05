#!/usr/bin/env python

import unittest
import sys
import brubeck
from handlers.method_handlers import simple_handler_method
from brubeck.request_handling import Brubeck, WebMessageHandler, JSONMessageHandler
from brubeck.mongrel2 import to_bytes, Request
from brubeck.request_handling import(
    cookie_encode, cookie_decode,
    cookie_is_encoded, http_response
)
from handlers.object_handlers import(
    SimpleWebHandlerObject, CookieWebHandlerObject,
    SimpleJSONHandlerObject, CookieAddWebHandlerObject,
    PrepareHookWebHandlerObject, InitializeHookWebHandlerObject
)

""" our simple messages for testing """
HTTP_REQUEST_BRUBECK = file('./fixtures/http_request_brubeck.txt','r').read()

HTTP_REQUEST_ROOT = file('./fixtures/http_request_root.txt','r').read()

HTTP_REQUEST_ROOT_WITH_COOKIE = file('./fixtures/http_request_root_with_cookie.txt','r').read()

""" our test body text """
TEST_BODY_METHOD_HANDLER = file('./fixtures/test_body_method_handler.txt','r').read().rstrip('\n')
TEST_BODY_OBJECT_HANDLER = file('./fixtures/test_body_object_handler.txt','r').read().rstrip('\n')

HTTP_RESPONSE_OBJECT_ROOT =      'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(TEST_BODY_OBJECT_HANDLER)) + '\r\n\r\n' + TEST_BODY_OBJECT_HANDLER
HTTP_RESPONSE_METHOD_ROOT =      'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(TEST_BODY_METHOD_HANDLER)) + '\r\n\r\n' + TEST_BODY_METHOD_HANDLER
HTTP_RESPONSE_JSON_OBJECT_ROOT = 'HTTP/1.1 200 OK\r\nContent-Length: 90\r\n\r\n{"status_code":200,"status_msg":"OK","message":"Take five dude","timestamp":1320456118809}'

HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE = 'HTTP/1.1 200 OK\r\nSet-Cookie: key=value\r\nContent-Length: ' + str(len(TEST_BODY_OBJECT_HANDLER)) + '\r\n\r\n' + TEST_BODY_OBJECT_HANDLER

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

class MockMessage(object):
    """ we are a static zmq message """
    def __init__(self, path = '/', msg = HTTP_REQUEST_ROOT):
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
        routes = [ (r'^/', simple_handler_method), (r'^/brubeck', simple_handler_method) ]
        self.app.init_routes( routes )

        """ Make sure we have two routes """
        self.assertEqual(len(self.app._routes), 2)

    def test_init_routes_with_objects(self):
        """ Make sure we have no routes """
        self.assertEqual(hasattr(self.app, '_routes'), False)

        """ Create a tuple of routes with object handlers """
        routes = [(r'^/', SimpleWebHandlerObject), (r'^/brubeck', SimpleWebHandlerObject)]
        self.app.init_routes( routes )

        """ Make sure we have two routes """
        self.assertEqual(len(self.app._routes), 2)

    def test_init_routes_with_objects_and_methods(self):
        """ Make sure we have no routes """
        self.assertEqual(hasattr(self.app, '_routes'), False)

        """ Create a tuple of routes with method handlers """
        routes = [(r'^/', SimpleWebHandlerObject), (r'^/brubeck', simple_handler_method)]
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

    def test_web_request_handling_with_object(self):
        self.setup_route_with_object()
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT))
        self.assertEqual(HTTP_RESPONSE_OBJECT_ROOT, response)

    def test_web_request_handling_with_method(self):
        self.setup_route_with_method()
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT))
        self.assertEqual(HTTP_RESPONSE_METHOD_ROOT, response)

    def test_json_request_handling_with_object(self):
        self.app.add_route_rule(r'^/$',SimpleJSONHandlerObject)
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT))
        self.assertEqual(HTTP_RESPONSE_JSON_OBJECT_ROOT, response)

    def test_request_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/$',CookieWebHandlerObject)
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT_WITH_COOKIE))
        self.assertEqual(HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE, response)

    def test_request_with_cookie_response_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/$',CookieWebHandlerObject)
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT_WITH_COOKIE))
        self.assertEqual(HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE, response)

    def test_request_without_cookie_response_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/$',CookieAddWebHandlerObject)
        response = route_message(self.app, Request.parse_msg(HTTP_REQUEST_ROOT))
        self.assertEqual(HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE, response)

    def test_build_http_response(self):
        response = http_response(TEST_BODY_OBJECT_HANDLER, 200, 'OK', dict())
        self.assertEqual(HTTP_RESPONSE_OBJECT_ROOT, response)

    def test_handler_initialize_hook(self):
        handler = InitializeHookWebHandlerObject(self.app, Request.parse_msg(HTTP_REQUEST_ROOT))
        self.assertEqual(handler(), HTTP_RESPONSE_OBJECT_ROOT)

    def test_handler_prepare_hook(self):
        handler = PrepareHookWebHandlerObject(self.app, Request.parse_msg(HTTP_REQUEST_ROOT))
        self.assertEqual(handler(), HTTP_RESPONSE_OBJECT_ROOT)

    """ some helper functions """
    def setup_route_with_object(self, url_pattern='^/$'):
        self.app.add_route_rule(url_pattern,SimpleWebHandlerObject)

    def setup_route_with_method(self, url_pattern='^/$'):
        method = simple_handler_method
        self.app.add_route_rule(url_pattern, method)

""" This will run our tests """
if __name__ == '__main__':
    unittest.main()
