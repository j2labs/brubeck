from brubeck.request_handling import http_response

def simple_handler_method(self, application, *args):
    """" dummy request action """
    return http_response(file('./fixtures/test_body_method_handler.txt','r').read().rstrip('\n'), 200, 'OK', dict())

