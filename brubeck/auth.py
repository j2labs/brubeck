"""Authentication functions are offered here in three groups.

    1. The mechanics of auth, like generating a hex digest or assembling the
       data.

    2. Tools for applying auth requirements to functions, eg. decorators.

    3. Mixins for adding authenticaiton handling to MessageHandler's and
       Document classes
"""

import bcrypt
import functools
import logging


###
### Password Helpers
###

BCRYPT = 'bcrypt'

PASSWD_DELIM = '|||'

def gen_hexdigest(raw_password, algorithm=BCRYPT, salt=None):
    """Takes the algorithm, salt and password and uses Python's
    hashlib to produce the hash. Currently only supports bcrypt.
    """
    if raw_password is None:
        raise ValueError('No empty passwords, fool')
    if algorithm == BCRYPT:
        # bcrypt has a special salt
        if salt is None:
            salt = bcrypt.gensalt()
        return (algorithm, salt, bcrypt.hashpw(raw_password, salt))
    raise ValueError('Unknown password algorithm')

def build_passwd_line(algorithm, salt, digest):
    """Simply takes the inputs for a passwd entry and puts them
    into the convention for storage
    """
    return PASSWD_DELIM.join([algorithm, salt, digest])

def split_passwd_line(password_line):
    """Takes a password line and returns the line split by PASSWD_DELIM
    """
    return password_line.split(PASSWD_DELIM)


###
### Authentication decorators
###

def authenticated(method):
    """Decorate request handler methods with this to require that the user be
    logged in. Works by checking for the existence of self.current_user as set
    by a RequestHandler's prepare() function.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            return self.render_error(self._AUTH_FAILURE)
        return method(self, *args, **kwargs)
    return wrapper

def web_authenticated(method):
    """Same as `authenticated` except it redirects a user to the login page
    specified by self.application.login_url
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if self.application.login_url is not None:
                return self.redirect(self.application.login_url)
            else:
                error = 'web_authentication called with undefined <login_url>'
                logging.error(error)
                return self.render_error(self._SERVER_ERROR)
        return method(self, *args, **kwargs)
    return wrapper


###
### Mixins to extend MessageHandlers with auth funcitons
###

class UserHandlingMixin(object):
    """A request handler that uses this mixin can also use the decorators
    above. This mixin is intended to make the interaction with authentication
    generic without insisting on a particular strategy.
    """
    
    @property
    def current_user(self):
        """The authenticated user for this message.

        Determined by either get_current_user, which you can override to
        set the user based on, e.g., a cookie. If that method is not

        overridden, this method always returns None.

        We lazy-load the current user the first time this method is called
        and cache the result after that.
        """
        if not hasattr(self, "_current_user"):
            self._current_user = self.get_current_user()
        return self._current_user        

    def get_current_user(self):
        """Override to determine the current user from, e.g., a cookie.
        """
        return None

    @property
    def current_userprofile(self):
        """Same idea for the user's profile
        """
        if not hasattr(self, "_current_userprofile"):
            self._current_userprofile = self.get_current_userprofile()
        return self._current_userprofile

    def get_current_userprofile(self):
        """Override to determine the current user
        """
        return None
