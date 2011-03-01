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

def authenticated(method, error_status=-2):
    """Decorate request handler methods with this to require that the user be
    logged in. Works by checking for the existence of self.current_user as set
    by a RequestHandler's prepare() function.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            self.set_status(error_status)
            raise self
        return method(self, *args, **kwargs)
    return wrapper

def web_authenticated(method):
    """Same as authenticated but uses a 401 error status
    """
    return authenticated(method, error_status=401)


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
        """Override to determine the current user from, e.g., a cookie."""
        return None

