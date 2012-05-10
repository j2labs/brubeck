#!/usr/bin/env python

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.connections import Mongrel2Connection
from brubeck.models import User
from brubeck.auth import authenticated, UserHandlingMixin
import sys
import logging

### Hardcode a user for the demo
demo_user = User.create_user('jd', 'foo')

class DemoHandler(WebMessageHandler, UserHandlingMixin):
    def get_current_user(self):
        """Attempts to load authentication credentials from a request and validate
        them. Returns an instantiated User if credentials were good.

        `get_current_user` is a callback triggered by decorating a function
        with @authenticated.
        """
        username = self.get_argument('username')
        password = self.get_argument('password')

        if demo_user.username != username:
            logging.error('Auth fail: username incorrect')
            return
        
        if not demo_user.check_password(password):
            logging.error('Auth fail: password incorrect')
            return
        
        logging.info('Access granted for user: %s' % username)
        return demo_user
    
    @authenticated
    def post(self):
        """Requires username and password."""
        self.set_body('%s logged in successfully!' % (self.current_user.username))
        return self.render()


config = {
    'msg_conn': Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
    'handler_tuples': [(r'^/brubeck', DemoHandler)],
}

app = Brubeck(**config)
app.run()
