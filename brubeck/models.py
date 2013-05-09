###
### DictShield documents
###

from schematics.models import Model
from schematics.types import (StringType,
                              BooleanType,
                              URLType,
                              EmailType,
                              LongType)


import auth
from timekeeping import curtime
from datamosh import OwnedModelMixin, StreamedModelMixin

import re


###
### User Document
###

class User(Model):
    """Bare minimum to have the concept of a User.
    """
    username = StringType(max_length=30, required=True)
    password = StringType(max_length=128)

    is_active = BooleanType(default=False)
    last_login = LongType(default=curtime)
    date_joined = LongType(default=curtime)

    username_regex = re.compile('^[A-Za-z0-9._]+$')
    username_min_length = 2

    class Options:
        roles = {
            'owner': blacklist('password', 'is_active'),
        }

    def __unicode__(self):
        return u'%s' % (self.username)

    def set_password(self, raw_passwd):
        """Generates bcrypt hash and salt for storing a user's password. With
        bcrypt, the salt is kind of redundant, but this format stays friendly
        to other algorithms.
        """
        (algorithm, salt, digest) = auth.gen_hexdigest(raw_passwd)
        self.password = auth.build_passwd_line(algorithm, salt, digest)

    def check_password(self, raw_password):
        """Compares raw_password to password stored for user. Updates
        self.last_login on success.
        """
        algorithm, salt, hash = auth.split_passwd_line(self.password)
        (_, _, user_hash) = auth.gen_hexdigest(raw_password,
                                               algorithm=algorithm, salt=salt)
        if hash == user_hash:
            self.last_login = curtime()
            return True
        else:
            return False

    @classmethod
    def create_user(cls, username, password, email=str()):
        """Creates a user document with given username and password
        and saves it.

        Validation occurs only for email argument. It makes no assumptions
        about password format.
        """
        now = curtime()

        username = username.lower()
        email = email.strip()
        email = email.lower()

        # Username must pass valid character range check.
        if not cls.username_regex.match(username):
            warning = 'Username failed character validation - username_regex'
            raise ValueError(warning)

        # Caller should handle validation exceptions
        cls.validate_class_partial(dict(email=email))

        user = cls(username=username, email=email, date_joined=now)
        user.set_password(password)
        return user


###
### UserProfile
###

class UserProfile(Model, OwnedModelMixin, StreamedModelMixin):
    """The basic things a user profile tends to carry. Isolated in separate
    class to keep separate from private data.
    """
    # Provided by OwnedModelMixin
    #owner_id = ObjectIdField(required=True)
    #owner_username = StringField(max_length=30, required=True)

    # streamable # provided by StreamedModelMixin now
    #created_at = MillisecondField()
    #updated_at = MillisecondField()

    # identity info
    name = StringType(max_length=255)
    email = EmailType(max_length=100)
    website = URLType(max_length=255)
    bio = StringType(max_length=100)
    location_text = StringType(max_length=100)
    avatar_url = URLType(max_length=255)

    class Options:
        roles = {
            'owner': blacklist('owner_id'),
        }

    def __init__(self, *args, **kwargs):
        super(UserProfile, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'%s' % (self.name)
