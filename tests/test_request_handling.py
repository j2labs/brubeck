#!/usr/bin/env python

import unittest
import sys
import brubeck
from handlers.method_handlers import simple_handler_method
from brubeck.request_handling import Brubeck, WebMessageHandler, JSONMessageHandler
from brubeck.connections import to_bytes, Request, WSGIConnection
from brubeck.request_handling import(
    cookie_encode, cookie_decode,
    cookie_is_encoded, http_response
)
from handlers.object_handlers import(
    SimpleWebHandlerObject, CookieWebHandlerObject,
    SimpleJSONHandlerObject, CookieAddWebHandlerObject,
    PrepareHookWebHandlerObject, InitializeHookWebHandlerObject
)
from fixtures import request_handler_fixtures as FIXTURES

###
### Message handling (non)coroutines for testing
###
def route_message(application, message):
    handler = application.route_message(message)
    return request_handler(application, message, handler)

def request_handler(application, message, handler):
    if callable(handler):
        return handler()

class MockMessage(object):
    """ we are enough of a message to test routing rules message """
    def __init__(self, path = '/', msg = FIXTURES.HTTP_REQUEST_ROOT):
        self.path = path
        self.msg = msg

    def get(self):
       return self.msg
        
class TestRequestHandling(unittest.TestCase):
    """
    a test class for brubeck's request_handler
    """

    def setUp(self):
        """ will get run for each test """
        config = {
            'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
            'msg_conn': WSGIConnection()
        }
        self.app = Brubeck(**config)
    ##
    ## our actual tests( test _xxxx_xxxx(self) ) 
    ##
    def test_add_route_rule_method(self):
	# Make sure we have no routes
        self.assertEqual(hasattr(self.app,'_routes'),False)

        # setup a route
        self.setup_route_with_method()

        # Make sure we have some routes
        self.assertEqual(hasattr(self.app,'_routes'),True)

        # Make sure we have exactly one route
        self.assertEqual(len(self.app._routes),1)

    def test_init_routes_with_methods(self):
        # Make sure we have no routes
        self.assertEqual(hasattr(self.app, '_routes'), False)

        # Create a tuple with routes with method handlers
        routes = [ (r'^/', simple_handler_method), (r'^/brubeck', simple_handler_method) ]
        # init our routes
        self.app.init_routes( routes )

        # Make sure we have two routes
        self.assertEqual(len(self.app._routes), 2)

    def test_init_routes_with_objects(self):
        # Make sure we have no routes
        self.assertEqual(hasattr(self.app, '_routes'), False)

        # Create a tuple of routes with object handlers
        routes = [(r'^/', SimpleWebHandlerObject), (r'^/brubeck', SimpleWebHandlerObject)]
        self.app.init_routes( routes )

        # Make sure we have two routes
        self.assertEqual(len(self.app._routes), 2)

    def test_init_routes_with_objects_and_methods(self):
        # Make sure we have no routes
        self.assertEqual(hasattr(self.app, '_routes'), False)

        # Create a tuple of routes with a method handler and an object handler
        routes = [(r'^/', SimpleWebHandlerObject), (r'^/brubeck', simple_handler_method)]
        self.app.init_routes( routes )

        # Make sure we have two routes
        self.assertEqual(len(self.app._routes), 2)

    def test_add_route_rule_object(self):
        # Make sure we have no routes
        self.assertEqual(hasattr(self.app,'_routes'),False)
        self.setup_route_with_object()

        # Make sure we have some routes
        self.assertEqual(hasattr(self.app,'_routes'),True)

        # Make sure we have exactly one route
        self.assertEqual(len(self.app._routes),1)

    def test_brubeck_handle_request_with_object(self):
        # set up our route
        self.setup_route_with_object()

        # Make sure we get a handler back when we request one
        message = MockMessage(path='/')
        handler = self.app.route_message(message)
        self.assertNotEqual(handler,None)

    def test_brubeck_handle_request_with_method(self):
        # We ran tests on this already, so assume it works
        self.setup_route_with_method()

        # Make sure we get a handler back when we request one
        message = MockMessage(path='/')
        handler = self.app.route_message(message)
        self.assertNotEqual(handler,None)

    def test_cookie_handling(self):
        # set our cookie key and values
        cookie_key = 'my_key'
        cookie_value = 'my_secret'

        # encode our cookie
        encoded_cookie = cookie_encode(cookie_value, cookie_key)

        # Make sure we do not contain our value (i.e. we are really encrypting)
        self.assertEqual(encoded_cookie.find(cookie_value) == -1, True)

        # Make sure we are an encoded cookie using the function
        self.assertEqual(cookie_is_encoded(encoded_cookie), True)

        # Make sure after decoding our cookie we are the same as the unencoded cookie
        decoded_cookie_value = cookie_decode(encoded_cookie, cookie_key)
        self.assertEqual(decoded_cookie_value, cookie_value)
    
    ##
    ## test a bunch of very simple requests making sure we get the expected results
    ##
    def test_web_request_handling_with_object(self):
        self.setup_route_with_object()
        result = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(FIXTURES.HTTP_RESPONSE_OBJECT_ROOT, response)

    def test_web_request_handling_with_method(self):
        self.setup_route_with_method()
        response = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        self.assertEqual(FIXTURES.HTTP_RESPONSE_METHOD_ROOT, response)

    def test_json_request_handling_with_object(self):
        self.app.add_route_rule(r'^/$',SimpleJSONHandlerObject)
        result = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(FIXTURES.HTTP_RESPONSE_JSON_OBJECT_ROOT, response)

    def test_request_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/$',CookieWebHandlerObject)
        result = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT_WITH_COOKIE))
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(FIXTURES.HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE, response)

    def test_request_with_cookie_response_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/$',CookieWebHandlerObject)
        result = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT_WITH_COOKIE))
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(FIXTURES.HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE, response)

    def test_request_without_cookie_response_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/$',CookieAddWebHandlerObject)
        result = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(FIXTURES.HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE, response)

    def test_build_http_response(self):
        response = http_response(FIXTURES.TEST_BODY_OBJECT_HANDLER, 200, 'OK', dict())
        self.assertEqual(FIXTURES.HTTP_RESPONSE_OBJECT_ROOT, response)

    def test_handler_initialize_hook(self):
        ## create a handler that sets the expected body(and headers) in the initialize hook
        handler = InitializeHookWebHandlerObject(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        result = handler()
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(response, FIXTURES.HTTP_RESPONSE_OBJECT_ROOT)

    def test_handler_prepare_hook(self):
        # create a handler that sets the expected body in the prepare hook
        handler = PrepareHookWebHandlerObject(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        result = handler()
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(response, FIXTURES.HTTP_RESPONSE_OBJECT_ROOT)

    ##
    ## some simple helper functions to setup a route """
    ##
    def setup_route_with_object(self, url_pattern='^/$'):
        self.app.add_route_rule(url_pattern,SimpleWebHandlerObject)

    def setup_route_with_method(self, url_pattern='^/$'):
        method = simple_handler_method
        self.app.add_route_rule(url_pattern, method)

##
## This will run our tests
##
if __name__ == '__main__':
    unittest.main()
