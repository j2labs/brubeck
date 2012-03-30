import os
##
## setup our simple messages for testing """
##
dir = os.path.abspath(__file__)[0:len(os.path.abspath(__file__))-28] + '/'

HTTP_REQUEST_BRUBECK = file( dir + 'http_request_brubeck.txt','r').read()

HTTP_REQUEST_ROOT = file(dir + 'http_request_root.txt','r').read()

HTTP_REQUEST_ROOT_WITH_COOKIE = file(dir + 'http_request_root_with_cookie.txt','r').read()

##
## our test body text
##
TEST_BODY_METHOD_HANDLER = file(dir + 'test_body_method_handler.txt','r').read().rstrip('\n')
TEST_BODY_OBJECT_HANDLER = file(dir + 'test_body_object_handler.txt','r').read().rstrip('\n')

##
##  setup our expected reponses
##
HTTP_RESPONSE_OBJECT_ROOT =      'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(TEST_BODY_OBJECT_HANDLER)) + '\r\n\r\n' + TEST_BODY_OBJECT_HANDLER
HTTP_RESPONSE_METHOD_ROOT =      'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(TEST_BODY_METHOD_HANDLER)) + '\r\n\r\n' + TEST_BODY_METHOD_HANDLER
HTTP_RESPONSE_JSON_OBJECT_ROOT = 'HTTP/1.1 200 OK\r\nContent-Length: 90\r\nContent-Type: application/json\r\n\r\n{"status_code":200,"status_msg":"OK","message":"Take five dude","timestamp":1320456118809}'

HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE = 'HTTP/1.1 200 OK\r\nSet-Cookie: key=value\r\nContent-Length: ' + str(len(TEST_BODY_OBJECT_HANDLER)) + '\r\n\r\n' + TEST_BODY_OBJECT_HANDLER

