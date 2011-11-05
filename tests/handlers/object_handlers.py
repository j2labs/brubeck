from brubeck.request_handling import Brubeck, WebMessageHandler, JSONMessageHandler

""" our test body text """
TEST_BODY_METHOD_HANDLER = file('./fixtures/test_body_method_handler.txt','r').read().rstrip('\n')
TEST_BODY_OBJECT_HANDLER = file('./fixtures/test_body_object_handler.txt','r').read().rstrip('\n')


class SimpleWebHandlerObject(WebMessageHandler):
    def get(self):
        self.set_body(TEST_BODY_OBJECT_HANDLER)
        return self.render()

class CookieWebHandlerObject(WebMessageHandler):
    def get(self):
        self.set_cookie("key", self.get_cookie("key"));
        self.set_body(TEST_BODY_OBJECT_HANDLER)
        return self.render()

class SimpleJSONHandlerObject(JSONMessageHandler):
    def get(self):
        self.add_to_payload('message', 'Take five dude')
        self.set_status(200)
        """ we only set time so it matches our expected response """
        self.add_to_payload("timestamp",1320456118809)
        return self.render()

class CookieAddWebHandlerObject(WebMessageHandler):
    def get(self):
        self.set_cookie("key", "value");
        self.set_body(TEST_BODY_OBJECT_HANDLER)
        return self.render()

class PrepareHookWebHandlerObject(WebMessageHandler):
    def get(self):
        return self.render()

    def prepare(self):
        self.set_body(TEST_BODY_OBJECT_HANDLER)

class InitializeHookWebHandlerObject(WebMessageHandler):
    def get(self):
        return self.render()

    def initialize(self):
        self.headers = dict()
        self.set_body(TEST_BODY_OBJECT_HANDLER)

