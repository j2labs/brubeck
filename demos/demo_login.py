#!/usr/bin/env python

import sys
import logging
from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.models import User
from brubeck.auth import web_authenticated, UserHandlingMixin
from brubeck.templating import Jinja2Rendering, load_jinja2_env

###
### Hardcoded authentication
###

demo_user = User.create_user('jd', 'foo')

class CustomAuthMixin(WebMessageHandler, UserHandlingMixin):
    """This Mixin provides a `get_current_user` implementation that
    validates auth against our hardcoded user: `demo_user`
    """
    def get_current_user(self):
        """Attempts to load user information from cookie. If that
        fails, it looks for credentials as arguments.

        If then attempts auth with the found credentials.
        """
        # Try loading credentials from cookie
        username = self.get_cookie('username')
        password = self.get_cookie('password')

        # Fall back to args if cookie isn't provided
        if username is None or password is None:
            username = self.get_argument('username')
            password = self.get_argument('password')

        if demo_user.username != username:
            logging.error('Auth fail: bad username')
            return
            
        if not demo_user.check_password(password):
            logging.error('Auth fail: bad password')
            return
        
        logging.debug('Access granted for user: %s' % username)
        self.set_cookie('username', username) # DEMO: Don't actually put a
        self.set_cookie('password', password) # password in a cookie...
        
        return demo_user


###
### Handlers
###

class LandingHandler(CustomAuthMixin, Jinja2Rendering):
    @web_authenticated
    def get(self):
        """Landing page. Forbids access without authentication
        """
        return self.render_template('landing.html')


class LoginHandler(CustomAuthMixin, Jinja2Rendering):
    def get(self):
        """Offers login form to user
        """
        return self.render_template('login.html')
    
    @web_authenticated
    def post(self):
        """Checks credentials with decorator and sends user authenticated
        users to the landing page.
        """
        return self.redirect('/')


class LogoutHandler(CustomAuthMixin, Jinja2Rendering):
    def get(self):
        """Clears cookie and sends user to login page
        """
        self.delete_cookies()
        return self.redirect('/login')


###
### Configuration
###
    
handler_tuples = [
    (r'^/login', LoginHandler),
    (r'^/logout', LogoutHandler),
    (r'^/', LandingHandler),
]

config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': handler_tuples,
    'template_loader': load_jinja2_env('./templates/login'),
    'login_url': '/login',
}

app = Brubeck(**config)
app.run()
