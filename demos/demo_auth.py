#!/usr/bin/env python


"""This is a rough prototype
"""

import sys

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.models import User
from brubeck.auth import web_authenticated, UserHandlingMixin

import logging
logging.basicConfig(**{'level': logging.DEBUG})

class DemoHandler(WebMessageHandler, UserHandlingMixin):
    def get_current_user(self):
        """Receives authentication credentials from a user and attempts
        to load the relevant user from a database.

        Values hardcoded for the demo.
        """
        username = self.get_argument('username')
        password = self.get_argument('password')
        # hardcode the username and password for the demo
        demo_user = User.create_user('jd', 'foo')
        # instead of loading the user by username, we'll match against
        # the hardcoded value
        if demo_user.username != username:
            logging.debug('Auth fail: username incorrect')
            return
        # attach user instance to request handler
        if demo_user.check_password(password):
            logging.debug('Authentication passed')
            return demo_user
        else:
            logging.debug('Auth fail: password incorrect')
    
    @web_authenticated
    def post(self):
        """Function called for HTTP POST. Requires username and password."""
        logging.debug('DemoHandler.post() calling .get()')
        self.set_body('You logged in successfully!')
        self.set_status(200)
        return self.render()

        
if __name__ == '__main__':
    pull_addr = 'ipc://127.0.0.1:9999'
    pub_addr = 'ipc://127.0.0.1:9998'

    # Make sure mongrel2's config is in sync with this.
    handler_tuples = [(r'^/brubeck', DemoHandler)]

    app = Brubeck((pull_addr, pub_addr), handler_tuples)
    app.run()
