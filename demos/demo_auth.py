#!/usr/bin/env python

import sys
from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.models import User
from brubeck.auth import web_authenticated, UserHandlingMixin

### Hardcode a user for the demo
demo_user = User.create_user('jd', 'foo')

class DemoHandler(WebMessageHandler, UserHandlingMixin):
    def get_current_user(self):
        """Receives authentication credentials from a user and attempts
        to load the relevant user from a database.

        `get_current_user` is a callback triggered by decorating a function
        with @web_authenticated.
        """
        username = self.get_argument('username')
        password = self.get_argument('password')

        if demo_user.username != username:
            logging.debug('Auth fail: username incorrect')
            return
        
        if not demo_user.check_password(password):
            logging.debug('Auth fail: password incorrect')
            return
        
        return demo_user
    
    @web_authenticated
    def post(self):
        """Requires username and password."""
        self.set_body('You logged in successfully!')
        self.set_status(200)
        return self.render()

        
pull_addr = 'ipc://127.0.0.1:9999'
pub_addr = 'ipc://127.0.0.1:9998'
handler_tuples = [(r'^/brubeck', DemoHandler)]

app = Brubeck((pull_addr, pub_addr), handler_tuples)
app.run()
