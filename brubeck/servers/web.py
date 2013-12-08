from . import Server
from ..handlers import web as web_handlers

class WebServer(Server):
    def __init__(self, cookie_secret=None, login_route=None, **kw):
        if 'default_handler' not in kw:
            kw['default_handler'] = web_handlers.WebMessageHandler

        super(WebServer, self).__init__(**kw)

        self.cookie_secret = cookie_secret
        self.login_route = login_route
        

